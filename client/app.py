"""Flask web dashboard that visualizes incoming MQTT device data."""

from __future__ import annotations

import atexit
import json
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from flask import Flask, jsonify, render_template

import paho.mqtt.client as mqtt


MQTT_BROKER = "mqtt.iotserver.uz"
MQTT_PORT = 1883
MQTT_USERNAME = "userTTPU"
MQTT_PASSWORD = "mqttpass"
TOPIC_LIGHT = "ttpu/iot/maqsud/sensors/light"
TOPIC_BUTTON = "ttpu/iot/maqsud/events/button"
LIGHT_MAX = 4096
MAX_EVENT_HISTORY = 25


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


def _on_connect(client: mqtt.Client, _userdata: Any, _flags: Dict[str, Any], rc: int) -> None:
	if rc == 0:
		logger.info("Connected to MQTT broker %s", MQTT_BROKER)
		client.subscribe([(TOPIC_LIGHT, 0), (TOPIC_BUTTON, 0)])
		with state_lock:
			connection_state.update({"connected": True, "last_error": None})
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
		"topics": {"light": TOPIC_LIGHT, "button": TOPIC_BUTTON},
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
			for entry in button_events
		]

		connection_snapshot = {
			"connected": connection_state["connected"],
			"last_error": connection_state["last_error"],
			"last_message_at": connection_state["last_message_at"],
			"last_message_at_iso": _to_iso(connection_state["last_message_at"]),
		}

	payload = {
		"sensor": sensor_data,
		"events": events,
		"connection": connection_snapshot,
		"meta": {
			"topics": {"light": TOPIC_LIGHT, "button": TOPIC_BUTTON},
			"light_max": LIGHT_MAX,
		},
	}
	return jsonify(payload)


@app.route("/health")
def health() -> Any:
	with state_lock:
		healthy = mqtt_started and (connection_state["connected"] or connection_state["last_error"] is None)
	return jsonify({"status": "ok" if healthy else "degraded"})


if __name__ == "__main__":
	start_mqtt()
	app.run(host="0.0.0.0", port=8000, debug=False)
