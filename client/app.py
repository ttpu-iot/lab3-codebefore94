"""Flask web dashboard that visualizes incoming MQTT device data."""

from __future__ import annotations

import atexit
import json
import logging
import threading
import time
from collections import deque
from itertools import islice
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from flask import Flask, jsonify, render_template, request

import paho.mqtt.client as mqtt


MQTT_BROKER = "mqtt.iotserver.uz"
MQTT_PORT = 1883
MQTT_USERNAME = "userTTPU"
MQTT_PASSWORD = "mqttpass"
TOPIC_LIGHT = "ttpu/iot/maqsud/sensors/light"
TOPIC_BUTTON = "ttpu/iot/maqsud/events/button"
TOPIC_LEDS = {
	"red": "ttpu/iot/maqsud/led/red",
	"green": "ttpu/iot/maqsud/led/green",
	"blue": "ttpu/iot/maqsud/led/blue",
	"yellow": "ttpu/iot/maqsud/led/yellow",
}
TOPIC_DISPLAY = "ttpu/iot/maqsud/display"
LIGHT_MAX = 4096
MAX_EVENT_HISTORY = 25
VALID_LED_STATES = {"ON", "OFF"}


logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dashboard")


app = Flask(__name__, static_folder="static", template_folder="templates")


state_lock = threading.Lock()
latest_sensor: Dict[str, Optional[float]] = {"light": None, "timestamp": None}
button_events: deque[Dict[str, Any]] = deque(maxlen=MAX_EVENT_HISTORY)
connection_state: Dict[str, Any] = {
	"connected": False,
	"last_error": None,
	"last_message_at": None,
}

led_states: Dict[str, str] = {color: "OFF" for color in TOPIC_LEDS}
last_display_message: Dict[str, Any] = {"text": "", "timestamp": None}


mqtt_start_lock = threading.Lock()
mqtt_started = False
mqtt_client: Optional[mqtt.Client] = None


def _safe_timestamp(raw: Any) -> Optional[float]:
	"""Convert raw timestamp values to float seconds since epoch when possible."""

	if raw is None:
		return None
	try:
		return float(raw)
	except (TypeError, ValueError):
		return None


def _to_iso(timestamp: Optional[float]) -> Optional[str]:
	if not timestamp:
		return None
	try:
		return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
	except (OSError, OverflowError, ValueError, TypeError):
		return None


def _handle_light_payload(payload: Dict[str, Any]) -> None:
	light_value = payload.get("light")
	if not isinstance(light_value, (int, float)):
		logger.warning("Unexpected light payload: %s", payload)
		return

	timestamp = _safe_timestamp(payload.get("timestamp")) or time.time()
	clamped = max(0.0, min(float(light_value), float(LIGHT_MAX)))
	with state_lock:
		latest_sensor["light"] = clamped
		latest_sensor["timestamp"] = timestamp


def _handle_button_payload(payload: Dict[str, Any]) -> None:
	event_raw = payload.get("event")
	if not isinstance(event_raw, str):
		logger.warning("Unexpected button payload: %s", payload)
		return
	event = event_raw.strip().upper()
	if event not in {"PRESSED", "RELEASED"}:
		logger.warning("Unknown button event '%s'", event_raw)
		return

	timestamp = _safe_timestamp(payload.get("timestamp")) or time.time()
	entry = {
		"event": event,
		"timestamp": timestamp,
	}
	with state_lock:
		button_events.appendleft(entry)


def _handle_led_payload(topic: str, payload: Dict[str, Any]) -> None:
	state_raw = payload.get("state")
	if not isinstance(state_raw, str):
		logger.warning("Unexpected LED payload on %s: %s", topic, payload)
		return
	state = state_raw.strip().upper()
	if state not in VALID_LED_STATES:
		logger.warning("Unknown LED state '%s' on %s", state_raw, topic)
		return
	color = next((name for name, topic_name in TOPIC_LEDS.items() if topic_name == topic), None)
	if color is None:
		return
	with state_lock:
		led_states[color] = state


def _handle_display_payload(payload: Dict[str, Any]) -> None:
	text_raw = payload.get("text")
	if not isinstance(text_raw, str):
		logger.warning("Unexpected display payload: %s", payload)
		return
	text = text_raw[:16]
	with state_lock:
		last_display_message.update({"text": text, "timestamp": time.time()})


def _on_connect(client: mqtt.Client, _userdata: Any, _flags: Dict[str, Any], rc: int) -> None:
	if rc == 0:
		logger.info("Connected to MQTT broker %s", MQTT_BROKER)
		client.subscribe([(TOPIC_LIGHT, 0), (TOPIC_BUTTON, 0)])
		client.subscribe([(topic, 0) for topic in TOPIC_LEDS.values()])
		client.subscribe([(TOPIC_DISPLAY, 0)])
		with state_lock:
			connection_state.update({"connected": True, "last_error": None})
			led_snapshot = dict(led_states)
			display_snapshot = dict(last_display_message)
		for color, state in led_snapshot.items():
			try:
				client.publish(TOPIC_LEDS[color], json.dumps({"state": state}), qos=1, retain=True)
			except Exception as exc:  # pylint: disable=broad-except
				logger.debug("Failed to publish retained LED state for %s: %s", color, exc)
		if display_snapshot.get("text"):
			try:
				client.publish(TOPIC_DISPLAY, json.dumps({"text": display_snapshot["text"]}), qos=1, retain=True)
			except Exception as exc:  # pylint: disable=broad-except
				logger.debug("Failed to publish retained display text: %s", exc)
	else:
		logger.error("MQTT connection failed with code %s", rc)
		with state_lock:
			connection_state.update({
				"connected": False,
				"last_error": f"Connection failed (code {rc})",
			})


def _on_message(client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
	try:
		payload = json.loads(msg.payload.decode("utf-8"))
	except json.JSONDecodeError:
		logger.warning("Failed to decode MQTT payload on %s", msg.topic)
		return

	if msg.topic == TOPIC_LIGHT:
		_handle_light_payload(payload)
	elif msg.topic == TOPIC_BUTTON:
		_handle_button_payload(payload)
	elif msg.topic in TOPIC_LEDS.values():
		_handle_led_payload(msg.topic, payload)
	elif msg.topic == TOPIC_DISPLAY:
		_handle_display_payload(payload)
	else:
		logger.debug("Unhandled topic %s", msg.topic)

	with state_lock:
		connection_state["last_message_at"] = time.time()


def _on_disconnect(client: mqtt.Client, _userdata: Any, rc: int) -> None:
	reason = "clean" if rc == 0 else f"unexpected (code {rc})"
	logger.warning("Disconnected from MQTT broker: %s", reason)
	with state_lock:
		connection_state.update({
			"connected": False,
			"last_error": None if rc == 0 else f"Disconnected (code {rc})",
		})


def _build_mqtt_client() -> mqtt.Client:
	client = mqtt.Client(client_id=f"lab3-dashboard-{uuid4().hex[:8]}")
	client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
	client.on_connect = _on_connect
	client.on_message = _on_message
	client.on_disconnect = _on_disconnect
	client.reconnect_delay_set(min_delay=1, max_delay=30)
	client.enable_logger(logger)
	return client


def start_mqtt() -> None:
	global mqtt_started, mqtt_client
	with mqtt_start_lock:
		if mqtt_started:
			return

		mqtt_client = _build_mqtt_client()
		try:
			mqtt_client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
			mqtt_client.loop_start()
			mqtt_started = True
			logger.info("Started MQTT listener thread")
		except Exception as exc:  # pylint: disable=broad-except
			logger.exception("Unable to start MQTT client: %s", exc)
			with state_lock:
				connection_state.update({
					"connected": False,
					"last_error": str(exc),
				})


def _ensure_mqtt_running() -> None:
	if not mqtt_started:
		start_mqtt()


@atexit.register
def _shutdown_mqtt() -> None:
	if not mqtt_started or mqtt_client is None:
		return
	logger.info("Stopping MQTT client")
	mqtt_client.loop_stop()
	try:
		mqtt_client.disconnect()
	except Exception as exc:  # pylint: disable=broad-except
		logger.debug("MQTT disconnect raised %s", exc)


start_mqtt()


@app.route("/")
def index() -> str:
	context = {
		"mqtt_broker": MQTT_BROKER,
		"topics": {
			"light": TOPIC_LIGHT,
			"button": TOPIC_BUTTON,
			"leds": TOPIC_LEDS,
			"display": TOPIC_DISPLAY,
		},
	}
	return render_template("index.html", **context)


@app.route("/api/state")
def get_state() -> Any:
	with state_lock:
		sensor_data = None
		if latest_sensor["light"] is not None:
			sensor_data = {
				"light": latest_sensor["light"],
				"timestamp": latest_sensor["timestamp"],
				"timestamp_iso": _to_iso(latest_sensor["timestamp"]),
			}

		events = [
			{
				"event": entry["event"],
				"timestamp": entry["timestamp"],
				"timestamp_iso": _to_iso(entry["timestamp"]),
			}
			for entry in islice(button_events, 6)
		]

		connection_snapshot = {
			"connected": connection_state["connected"],
			"last_error": connection_state["last_error"],
			"last_message_at": connection_state["last_message_at"],
			"last_message_at_iso": _to_iso(connection_state["last_message_at"]),
		}

		led_snapshot = dict(led_states)
		display_snapshot = dict(last_display_message)

	payload = {
		"sensor": sensor_data,
		"events": events,
		"connection": connection_snapshot,
		"leds": led_snapshot,
		"display": {
			"text": display_snapshot.get("text", ""),
			"timestamp": display_snapshot.get("timestamp"),
			"timestamp_iso": _to_iso(display_snapshot.get("timestamp")),
		},
		"meta": {
			"topics": {
				"light": TOPIC_LIGHT,
				"button": TOPIC_BUTTON,
				"leds": TOPIC_LEDS,
				"display": TOPIC_DISPLAY,
			},
			"light_max": LIGHT_MAX,
		},
	}
	return jsonify(payload)


@app.route("/api/led/<color>", methods=["POST"])
def set_led_state(color: str) -> Any:
	color_key = color.lower()
	if color_key not in TOPIC_LEDS:
		return jsonify({"error": "Unknown LED color"}), 404

	data = request.get_json(silent=True) or {}
	state_raw = data.get("state")
	if state_raw is None:
		return jsonify({"error": "Missing 'state' field"}), 400
	state = str(state_raw).strip().upper()
	if state not in VALID_LED_STATES:
		return jsonify({"error": "State must be 'ON' or 'OFF'"}), 400

	_ensure_mqtt_running()

	with state_lock:
		led_states[color_key] = state
		led_snapshot = dict(led_states)

	topic = TOPIC_LEDS[color_key]
	if mqtt_client is None:
		logger.warning("LED update requested before MQTT client ready")
	else:
		payload = json.dumps({"state": state})
		try:
			mqtt_client.publish(topic, payload=payload, qos=1, retain=True)
		except Exception as exc:  # pylint: disable=broad-except
			logger.exception("Failed to publish LED state for %s: %s", color_key, exc)

	return jsonify({"color": color_key, "state": state, "leds": led_snapshot})


@app.route("/api/display", methods=["POST"])
def send_display_message() -> Any:
	data = request.get_json(silent=True) or {}
	text_raw = data.get("text", "")
	if not isinstance(text_raw, str):
		return jsonify({"error": "'text' must be a string"}), 400
	text = text_raw.strip()
	if not text:
		return jsonify({"error": "Text must not be empty"}), 400
	if len(text) > 16:
		return jsonify({"error": "Text must be 16 characters or fewer"}), 400

	_ensure_mqtt_running()

	with state_lock:
		last_display_message.update({"text": text, "timestamp": time.time()})
		display_snapshot = dict(last_display_message)

	if mqtt_client is None:
		logger.warning("Display update requested before MQTT client ready")
	else:
		payload = json.dumps({"text": text})
		try:
			mqtt_client.publish(TOPIC_DISPLAY, payload=payload, qos=1, retain=True)
		except Exception as exc:  # pylint: disable=broad-except
			logger.exception("Failed to publish display text: %s", exc)

	return jsonify({
		"display": {
			"text": display_snapshot.get("text", ""),
			"timestamp": display_snapshot.get("timestamp"),
			"timestamp_iso": _to_iso(display_snapshot.get("timestamp")),
		},
	})


@app.route("/health")
def health() -> Any:
	with state_lock:
		healthy = mqtt_started and (connection_state["connected"] or connection_state["last_error"] is None)
	return jsonify({"status": "ok" if healthy else "degraded"})


if __name__ == "__main__":
	start_mqtt()
	app.run(host="0.0.0.0", port=8000, debug=False)
