[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/N4XHFhiQ)
[![Open in Codespaces](https://classroom.github.com/assets/launch-codespace-2972f46106e565e64193e422d61a12cf1da4916b45550586e14ef0a7c637dd04.svg)](https://classroom.github.com/open-in-codespaces?assignment_repo_id=21381421)
# IoT 2025 - Lab 3 Template

# Lab 3 - ESP32 + MQTT + ArduinoJson

You need to finish following exercises

### Setup Configuration in this Wokwi Project template:

- RED LED - `D26`
- Green LED - `D27`
- Blue LED - `D14`
- Yellow LED - `D12`


- Button (Active high) - `D25`
- Light sensor (analog) - `D33`


- LCD I2C - SDA: `D21`
- LCD I2C - SCL: `D22`


<img src="esp32_wokwi_setup.png" alt="ESP32 Pin Configuration" width="70%">

----------
## MQTT Broker Credentials
- Broker: `broker address is also given in the telegram group`
- Port: `1883` (non-secure)
- Username: `given in the telegram group`
- Password: `given in the telegram group`
- Client ID: `must be unique, e.g., your name + lab3`

----------
## Topic Naming Convention (All Exercises)
All topics **must** start with `ttpu/iot/` followed by **your name** (lowercase, no spaces).

**Example for student "sardor":**
- `ttpu/iot/sardor/sensors/light`
- `ttpu/iot/sardor/events/button`
- `ttpu/iot/sardor/led/red`
- `ttpu/iot/sardor/led/green`
- `ttpu/iot/sardor/led/blue`
- `ttpu/iot/sardor/led/yellow`
- `ttpu/iot/sardor/display`

**Replace `studentname` with your actual name in all exercises below!**

----------
## Exercise 1: Basic MQTT Publish (Sensors + Events)

### Goal
Connect to MQTT broker and publish sensor data periodically + button events on state change.

### Requirements
- Connect to WiFi (`Wokwi-GUEST`, no password)
- Connect to MQTT broker using provided credentials
- Configure LED pins as OUTPUT (not used in this exercise, but initialize them)
- Configure button pin (`D25`) as INPUT
- Configure light sensor pin (`D33`) as analog input

### Publishing Tasks

#### 1. Periodic Publishing (every 5 seconds)
- **Topic:** `ttpu/iot/studentname/sensors/light`
- **Payload:** JSON with light sensor value and timestamp
- Read analog value from `D33`
- Get current Unix timestamp
- Create JSON and publish

**Example payload:**
```json
{
  "light": 2048,
  "timestamp": 1698681234
}
```

#### 2. Event-Based Publishing (on button state change)
- **Topic:** `ttpu/iot/studentname/events/button`
- **Payload:** JSON with event type and timestamp
- Detect button state change on `D25` (pressed or released)
- Use proper **button debouncing** (e.g., 50ms delay)
- Publish only when state changes (not continuously)

**Example payloads:**
```json
{
  "event": "PRESSED",
  "timestamp": 1698681240
}
```
```json
{
  "event": "RELEASED",
  "timestamp": 1698681245
}
```

### Serial Monitor Output
- Print WiFi connection status and IP address
- Print MQTT connection status
- Print every published message (topic + payload)

### Checklist
- [ ] ESP32 connects to `Wokwi-GUEST` WiFi
- [ ] ESP32 connects to MQTT broker with unique Client ID
- [ ] Light sensor data published every 5 seconds with correct JSON format
- [ ] Button press event published immediately when button is pressed
- [ ] Button release event published immediately when button is released
- [ ] No duplicate events (proper debouncing implemented)
- [ ] All messages printed to Serial Monitor

----------

## Exercise 2: MQTT Subscribe & Control LEDs

### Goal
Subscribe to MQTT topics and control LEDs based on received messages.

### Requirements
- Connect to WiFi (`Wokwi-GUEST`, no password)
- Connect to MQTT broker using provided credentials
- Configure 4 LED pins as OUTPUT: `D26` (Red), `D27` (Green), `D14` (Blue), `D12` (Yellow)
- Set all LEDs to LOW initially

### Subscription Tasks

#### Subscribe to 4 LED control topics:
1. `ttpu/iot/studentname/led/red` → controls Red LED (`D26`)
2. `ttpu/iot/studentname/led/green` → controls Green LED (`D27`)
3. `ttpu/iot/studentname/led/blue` → controls Blue LED (`D14`)
4. `ttpu/iot/studentname/led/yellow` → controls Yellow LED (`D12`)

#### Message Format
Each topic receives JSON messages with the following format:
```json
{
  "state": "ON"
}
```
or
```json
{
  "state": "OFF"
}
```

#### LED Control Logic
- Parse the incoming JSON message
- Extract the `"state"` field
- If `"state"` is `"ON"` → `digitalWrite(LED_PIN, HIGH)`
- If `"state"` is `"OFF"` → `digitalWrite(LED_PIN, LOW)`
- Handle malformed JSON gracefully (print error, don't crash)

### Serial Monitor Output
- Print WiFi connection status and IP address
- Print MQTT connection status
- Print every received message: topic, payload, and action taken

**Example:**
```
[MQTT] Received on ttpu/iot/sardor/led/red: {"state":"ON"}
[LED] Red LED -> ON

[MQTT] Received on ttpu/iot/sardor/led/blue: {"state":"OFF"}
[LED] Blue LED -> OFF
```

### Checklist
- [ ] ESP32 connects to WiFi and MQTT broker
- [ ] Subscribed to all 4 LED topics
- [ ] Red LED turns ON/OFF based on messages to `ttpu/iot/studentname/led/red`
- [ ] Green LED turns ON/OFF based on messages to `ttpu/iot/studentname/led/green`
- [ ] Blue LED turns ON/OFF based on messages to `ttpu/iot/studentname/led/blue`
- [ ] Yellow LED turns ON/OFF based on messages to `ttpu/iot/studentname/led/yellow`
- [ ] JSON parsing works correctly
- [ ] Malformed JSON handled without crashing
- [ ] All MQTT activity printed to Serial Monitor

----------

## Exercise 3: Bi-directional MQTT + LCD Display with Timestamp

### Goal
Combine LED control (subscribe), button events (publish), and display messages on LCD with Tashkent time.

### Requirements
- Connect to WiFi (`Wokwi-GUEST`, no password)
- Connect to MQTT broker using provided credentials
- Configure 4 LED pins as OUTPUT
- Configure button pin (`D25`) as INPUT
- Initialize LCD I2C display (address `0x27`, 16x2, `SDA: D21`, `SCL: D22`)
- Sync time with NTP server on startup (Tashkent timezone, UTC+5)

### Publishing Tasks

#### Button Events (on state change only)
- **Topic:** `ttpu/iot/studentname/events/button`
- **Payload:** JSON with event type and timestamp
- Same as Exercise 1 (detect button press/release with debouncing)

**Example payload:**
```json
{
  "event": "PRESSED",
  "timestamp": 1698681240
}
```

### Subscription Tasks

#### 1. LED Control (same as Exercise 2)
Subscribe to 4 topics:
- `ttpu/iot/studentname/led/red` → controls Red LED (`D26`)
- `ttpu/iot/studentname/led/green` → controls Green LED (`D27`)
- `ttpu/iot/studentname/led/blue` → controls Blue LED (`D14`)
- `ttpu/iot/studentname/led/yellow` → controls Yellow LED (`D12`)

**Message format:**
```json
{
  "state": "ON"
}
```

#### 2. Display Messages
- **Topic:** `ttpu/iot/studentname/display`
- **Payload:** JSON with text to display

**Example payload:**
```json
{
  "text": "Hello IoT Lab!"
}
```

### LCD Display Logic

#### Line 1: Display Message
- Show the last received text from `ttpu/iot/studentname/display` topic
- Maximum 16 characters (truncate if longer)
- Update only when a new message arrives

#### Line 2: Timestamp
- Show the **date and time** when the last display message was received
- Format: `DD/MM HH:MM:SS` (e.g., `30/10 14:35:20`)
- Use **Tashkent timezone** (UTC+5)
- Use NTP time synchronization: `configTime(18000, 0, "pool.ntp.org")`
- Update only when a new display message arrives

**Example LCD:**
```
Line 1: Hello IoT Lab!
Line 2: 30/10 14:35:20
```

### Serial Monitor Output
- Print WiFi connection status and IP address
- Print MQTT connection status
- Print NTP sync status
- Print all published button events
- Print all received LED control messages
- Print all received display messages
- Print LCD update confirmations

### Checklist
- [ ] ESP32 connects to WiFi and MQTT broker
- [ ] NTP time synchronized on startup (Tashkent timezone)
- [ ] Button press/release events published to `ttpu/iot/studentname/events/button`
- [ ] Subscribed to 4 LED control topics (Red, Green, Blue, Yellow)
- [ ] All 4 LEDs respond correctly to MQTT messages
- [ ] Subscribed to `ttpu/iot/studentname/display` topic
- [ ] LCD Line 1 shows received text message (max 16 chars)
- [ ] LCD Line 2 shows date/time when message was received (DD/MM HH:MM:SS format)
- [ ] LCD updates only when new display message arrives (not every loop)
- [ ] All MQTT and LCD activity printed to Serial Monitor

----------

## Quick Tips for All Exercises

### WiFi Connection
```cpp
#include <WiFi.h>
WiFi.begin("Wokwi-GUEST", "");
while (WiFi.status() != WL_CONNECTED) {
  delay(500);
}
Serial.println(WiFi.localIP());
```

### MQTT Connection
```cpp
#include <PubSubClient.h>
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

mqttClient.setServer("mqtt.iotserver.uz", 1883);
mqttClient.setCallback(callbackFunction);

while (!mqttClient.connected()) {
  mqttClient.connect("clientID", "username", "password");
}
```

### JSON Creation (Publishing)
```cpp
#include <ArduinoJson.h>
JsonDocument doc;
doc["light"] = analogRead(33);
doc["timestamp"] = time(nullptr);

char buffer[256];
serializeJson(doc, buffer);
mqttClient.publish("topic", buffer);
```

### JSON Parsing (Subscribing)
```cpp
void callback(char* topic, byte* payload, unsigned int length) {
  JsonDocument doc;
  deserializeJson(doc, payload, length);
  
  String state = doc["state"];
  if (state == "ON") {
    digitalWrite(LED_PIN, HIGH);
  }
}
```

### NTP Time Sync (Exercise 3)
```cpp
#include <time.h>
configTime(18000, 0, "pool.ntp.org"); // UTC+5 for Tashkent

struct tm timeinfo;
if (getLocalTime(&timeinfo)) {
  char buffer[20];
  strftime(buffer, sizeof(buffer), "%d/%m %H:%M:%S", &timeinfo);
  // Display on LCD Line 2
}
```

### LCD Display (Exercise 3)
```cpp
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 16, 2);

lcd.init();
lcd.backlight();
lcd.setCursor(0, 0);
lcd.print("Hello IoT!");
lcd.setCursor(0, 1);
lcd.print("30/10 14:35:20");
```

### Button Debouncing
```cpp
int lastButtonState = LOW;
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;

int reading = digitalRead(BUTTON_PIN);
if (reading != lastButtonState) {
  lastDebounceTime = millis();
}
if ((millis() - lastDebounceTime) > debounceDelay) {
  // Button state has changed
}
```

----------

## Tools Required
- **VS Code** with **PlatformIO** extension
- **Wokwi** extension for VS Code (free, registration required)
- MQTT client for testing (e.g., MQTT Explorer, MQTTX, or mosquitto_pub/sub)

----------

## Testing Your Code

### Exercise 1 Testing
Use an MQTT client to subscribe to your topics and verify messages:
```bash
mosquitto_sub -h mqtt.iotserver.uz -p 1883 -u username -P password -t "ttpu/iot/studentname/#" -v
```

### Exercise 2 Testing
Use an MQTT client to publish LED control messages:
```bash
mosquitto_pub -h mqtt.iotserver.uz -p 1883 -u username -P password -t "ttpu/iot/studentname/led/red" -m '{"state":"ON"}'
```

### Exercise 3 Testing
Publish display messages:
```bash
mosquitto_pub -h mqtt.iotserver.uz -p 1883 -u username -P password -t "ttpu/iot/studentname/display" -m '{"text":"Test Message"}'
```

----------

## Submission
- Submit your working code for all 3 exercises
- Include screenshots of Serial Monitor output
- Include screenshots of MQTT messages (from MQTT client)
- For Exercise 3: Include a photo/screenshot of LCD display showing message + timestamp

**Good luck!** 🚀
