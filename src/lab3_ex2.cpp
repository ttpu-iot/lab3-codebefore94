#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>


// GLOBAL DECLARATIONS
const int redLEDPin = 26;    // GPIO pin for Red LED
const int greenLEDPin = 27;  // GPIO pin for Green LED 
const int blueLEDPin = 14;   // GPIO pin for Blue LED
const int yellowLEDPin = 12; // GPIO pin for Yellow LED

// WiFi credentials
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// MQTT Broker settings
const char* mqtt_broker = "mqtt.iotserver.uz";  // Free public MQTT broker
const int mqtt_port = 1883;
const char* mqtt_username = "userTTPU";  // username given in the telegram group
const char* mqtt_password = "mqttpass";  // password given in the telegram group

const char* mqtt_topic_red = "ttpu/iot/maqsud/led/red";
const char* mqtt_topic_green = "ttpu/iot/maqsud/led/green";
const char* mqtt_topic_blue = "ttpu/iot/maqsud/led/blue";
const char* mqtt_topic_yellow = "ttpu/iot/maqsud/led/yellow";


WiFiClient espClient;
PubSubClient mqtt_client(espClient);


// Function to connect to WiFi
void connectWiFi();
// Callback function for received MQTT messages
void mqttCallback(char* topic, byte* payload, unsigned int length);
// Function to connect/reconnect to MQTT broker
void connectMQTT();

/*************************
 * SETUP
 */
void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(redLEDPin, OUTPUT);
  pinMode(greenLEDPin, OUTPUT);
  pinMode(blueLEDPin, OUTPUT);
  pinMode(yellowLEDPin, OUTPUT);

  digitalWrite(redLEDPin, LOW);
  digitalWrite(greenLEDPin, LOW);
  digitalWrite(blueLEDPin, LOW);
  digitalWrite(yellowLEDPin, LOW);
  
  Serial.println("\n===== MQTT Basic Example =====");
  Serial.println("Your Name, Lab 3 - Ex 2");
  
  // Connect to WiFi
  connectWiFi();
  
  // Setup MQTT
  mqtt_client.setServer(mqtt_broker, mqtt_port);
  mqtt_client.setCallback(mqttCallback);
  
  // Connect to MQTT broker
  connectMQTT();
}


/*************************
 * LOOP
 */
void loop() {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected! Reconnecting...");
    connectWiFi();
  }
  
  // Check MQTT connection
  if (!mqtt_client.connected()) {
    Serial.println("MQTT disconnected! Reconnecting...");
    connectMQTT();
  }
  
  // Process incoming MQTT messages
  mqtt_client.loop();
  
}

/*************************
 * FUNCTIONS
 */
//-------------------------------------------
// Function to connect to WiFi
void connectWiFi() 
{
  Serial.println("\nConnecting to WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

//-------------------------------------------
// Callback function for received MQTT messages
void mqttCallback(char* topic, byte* payload, unsigned int length) 
{
  Serial.print("Message received on topic: ");
  Serial.println(topic);

  int chosenLED = -1;

  String topicStr = String(topic);
  if (topicStr == String(mqtt_topic_red)) {
    chosenLED = redLEDPin;
  } 
  else if (topicStr == String(mqtt_topic_green)) {
    chosenLED = greenLEDPin;
  } 
  else if (topicStr == String(mqtt_topic_blue)) {
    chosenLED = blueLEDPin;
    
  } 
  else if (topicStr == String(mqtt_topic_yellow)) {
    chosenLED = yellowLEDPin;
  }
  
  // Convert payload to String
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.print("Message content: ");
  Serial.println(message);
  Serial.println("---");
  

  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, message.c_str());
  if (error) {
    Serial.print("Failed to parse JSON: ");
    Serial.println(error.c_str());
    return;
  }

  const char* state_cstr = doc["state"].is<const char*>() ? doc["state"].as<const char*>() : nullptr;
  String state_val = state_cstr ? String(state_cstr) : "";

  int ledState = -1;

  if (state_val == "ON"){
    ledState = HIGH;
  }
  else if (state_val == "OFF"){
    ledState = LOW;
  }

  if (chosenLED != -1 && ledState != -1) {
    digitalWrite(chosenLED, ledState);
  }
 
}

//-------------------------------------------
// Function to connect/reconnect to MQTT broker
void connectMQTT() 
{
  while (!mqtt_client.connected()) {
    Serial.println("Connecting to MQTT broker...");
    
    String client_id = "esp32-client-" + String(WiFi.macAddress());
    
    if (mqtt_client.connect(client_id.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("Connected to MQTT broker!");
      
      // Subscribe to topic
      mqtt_client.subscribe(mqtt_topic_red);
      mqtt_client.subscribe(mqtt_topic_green);
      mqtt_client.subscribe(mqtt_topic_blue);
      mqtt_client.subscribe(mqtt_topic_yellow);

      Serial.println("Subscribed to topics");
    } 
    else {
      Serial.print("MQTT connection failed, rc=");
      Serial.println(mqtt_client.state());
      Serial.println("Retrying in 5 seconds...");
      delay(5000);
    }
  }
}