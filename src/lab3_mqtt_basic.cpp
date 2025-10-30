#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>


// GLOBAL DECLARATIONS

// WiFi credentials
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// MQTT Broker settings
const char* mqtt_broker = "mqtt.iotserver.uz";  // Free public MQTT broker
const int mqtt_port = 1883;
const char* mqtt_username = "userTTPU";  // username given in the telegram group
const char* mqtt_password = "mqttpass";  // password given in the telegram group

const char* mqtt_topic_pub = "ttpu/iot/test/out";   // Topic to publish
const char* mqtt_topic_sub = "ttpu/iot/test/in";    // Topic to subscribe


WiFiClient espClient;
PubSubClient mqtt_client(espClient);

unsigned long lastPublishTime = 0;
const long publishInterval = 5000;  // Publish every 5 seconds
int messageCounter = 0;

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
  
  Serial.println("\n===== MQTT Basic Example =====");
  Serial.println("Your Name, Lab 3 - MQTT Basic");
  
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
  
  // Publish message every 5 seconds
  unsigned long currentTime = millis();
  if (currentTime - lastPublishTime >= publishInterval) {
    lastPublishTime = currentTime;
    
    messageCounter++;
    String message = "Hello from ESP32! Count: " + String(messageCounter);
    
    Serial.print("Publishing message: ");
    Serial.println(message);
    
    if (mqtt_client.publish(mqtt_topic_pub, message.c_str())) {
      Serial.println("Message published successfully!");
    } 
    else {
      Serial.println("Failed to publish message!");
    }
    Serial.println("---");
  }
}

/*************************
 * FUNCTIONS
 */
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

// Callback function for received MQTT messages
void mqttCallback(char* topic, byte* payload, unsigned int length) 
{
  Serial.print("Message received on topic: ");
  Serial.println(topic);
  
  // Convert payload to String
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("Message content: ");
  Serial.println(message);
  Serial.println("---");
}

// Function to connect/reconnect to MQTT broker
void connectMQTT() 
{
  while (!mqtt_client.connected()) {
    Serial.println("Connecting to MQTT broker...");
    
    String client_id = "esp32-client-" + String(WiFi.macAddress());
    
    if (mqtt_client.connect(client_id.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("Connected to MQTT broker!");
      
      // Subscribe to topic
      mqtt_client.subscribe(mqtt_topic_sub);
      Serial.print("Subscribed to topic: ");
      Serial.println(mqtt_topic_sub);
    } 
    else {
      Serial.print("MQTT connection failed, rc=");
      Serial.println(mqtt_client.state());
      Serial.println("Retrying in 5 seconds...");
      delay(5000);
    }
  }
}