#include <Arduino.h>
#include <Wire.h>
#include <hd44780.h>
#include <hd44780ioClass/hd44780_I2Cexp.h>

// GLOBAL DECLARATIONS

// LCD Configuration
hd44780_I2Cexp lcd;  // Auto-detect I2C address
const int LCD_COLS = 16;
const int LCD_ROWS = 2;

// Time tracking
unsigned long lastUpdate = 0;
const long updateInterval = 1000;  // Update every 1 second
int counter = 0;

// Default date and time (constant starting point)
const int START_YEAR = 2025;
const int START_MONTH = 1;
const int START_DAY = 15;
const int START_HOUR = 10;
const int START_MINUTE = 30;
const int START_SECOND = 0;

// Current time variables (seconds since start)
unsigned long elapsedSeconds = 0;

// Function to calculate current time
void calculateCurrentTime(int &hour, int &minute, int &second, int &day, int &month, int &year);

/*************************
 * SETUP
 */
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n===== LCD Basic Example =====");
  Serial.println("Your Name, Lab 3 - LCD Basic");
  
  // Initialize LCD
  int status = lcd.begin(LCD_COLS, LCD_ROWS);
  if (status) {
    Serial.println("LCD initialization failed!");
    Serial.print("Status code: ");
    Serial.println(status);
    hd44780::fatalError(status);
  }
  
  Serial.println("LCD initialized successfully!");

  // set contrast if needed
  lcd.setContrast(60); // Adjust contrast value as needed

  // set brightness if needed
  lcd.setBacklight(LOW); // Turn on backlight
  
  // Clear LCD and display initial message
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Initializing...");
  delay(1000);
  
  lcd.clear();
}

/*************************
 * LOOP
 */
void loop() {
  unsigned long currentTime = millis();
  
  // Update display every 1 second
  if (currentTime - lastUpdate >= updateInterval) {
    lastUpdate = currentTime;
    elapsedSeconds++;
    counter++;
    
    // Calculate current date and time
    int hour, minute, second, day, month, year;
    calculateCurrentTime(hour, minute, second, day, month, year);
    
    // Clear LCD
    lcd.clear();
    
    // Line 1: Counter
    lcd.setCursor(0, 0);
    lcd.print("Count=");
    lcd.print(counter);
    
    // Line 2: Date and Time (DD/MM/YYYY HH:MM:SS format - only HH:MM:SS fits on 16 chars)
    lcd.setCursor(0, 1);
    
    // Format: DD/MM HH:MM:SS (15 chars total)
    if (day < 10) lcd.print("0");
    lcd.print(day);
    lcd.print("/");
    if (month < 10) lcd.print("0");
    lcd.print(month);
    lcd.print(" ");
    if (hour < 10) lcd.print("0");
    lcd.print(hour);
    lcd.print(":");
    if (minute < 10) lcd.print("0");
    lcd.print(minute);
    lcd.print(":");
    if (second < 10) lcd.print("0");
    lcd.print(second);
    
    // Print to Serial Monitor as well
    Serial.print("Counter: ");
    Serial.print(counter);
    Serial.print(" | Date/Time: ");
    if (day < 10) Serial.print("0");
    Serial.print(day);
    Serial.print("/");
    if (month < 10) Serial.print("0");
    Serial.print(month);
    Serial.print("/");
    Serial.print(year);
    Serial.print(" ");
    if (hour < 10) Serial.print("0");
    Serial.print(hour);
    Serial.print(":");
    if (minute < 10) Serial.print("0");
    Serial.print(minute);
    Serial.print(":");
    if (second < 10) Serial.print("0");
    Serial.println(second);
  }
}

/**
 * Function to calculate current time
 */
void calculateCurrentTime(int &hour, int &minute, int &second, int &day, int &month, int &year) {
  unsigned long totalSeconds = START_HOUR * 3600 + START_MINUTE * 60 + START_SECOND + elapsedSeconds;
  
  // Calculate time components
  second = totalSeconds % 60;
  unsigned long totalMinutes = totalSeconds / 60;
  minute = totalMinutes % 60;
  unsigned long totalHours = totalMinutes / 60;
  hour = totalHours % 24;
  unsigned long totalDays = totalHours / 24;
  
  // Calculate date (simplified - doesn't account for different month lengths)
  day = START_DAY + totalDays;
  month = START_MONTH;
  year = START_YEAR;
  
  // Simple overflow handling (assuming 30-day months for simplicity)
  while (day > 30) {
    day -= 30;
    month++;
    if (month > 12) {
      month = 1;
      year++;
    }
  }
}