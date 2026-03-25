#include <LiquidCrystal.h>
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

// ===== WiFi Settings =====
const char* ssid = "projectiot";
const char* password = "projectiot";
const unsigned int localUdpPort = 4210;  // UDP port to listen

WiFiUDP udp;
char incomingPacket[255];

// ===== LCD Setup =====
LiquidCrystal lcd(D0, D1, D2, D3, D4, D5);

// ===== Motor & Buzzer Pins =====
const int motorPinPWM = D6; // PWM pin
const int motorPinDir = D7; // Direction pin
#define Buzzer D8

// Motor variables
int motorSpeed = 0;   // PWM value
int userSpeed = 0;    // Desired speed in km/h

// Buzzer variables
bool buzzerOn = false;
unsigned long buzzerStartTime = 0;
const unsigned long buzzerDuration = 2000; // 2 seconds

char receivedChar;

void setup() {
  Serial.begin(115200);

  // ===== Connect to WiFi =====
  WiFi.begin(ssid, password);
  lcd.begin(16, 2);
  lcd.setCursor(0,0);
  lcd.print("Connecting WiFi");
  lcd.setCursor(0,1);
  lcd.print("Please wait...");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("WiFi Connected");
  lcd.setCursor(0,1);
  lcd.print(WiFi.localIP());
  delay(2000);
  lcd.clear();

  udp.begin(localUdpPort);
  Serial.println("UDP listener started");

  pinMode(motorPinPWM, OUTPUT);
  pinMode(motorPinDir, OUTPUT);
  pinMode(Buzzer, OUTPUT);

  analogWrite(motorPinPWM, 0);
  digitalWrite(motorPinDir, LOW); // Forward

  lcd.setCursor(0,0);
  lcd.print("Waiting for Sign");
  lcd.setCursor(0,1);
  lcd.print("Data from UDP");
}

void loop() {
  // ===== Read UDP Packet =====
  int packetSize = udp.parsePacket();
  if (packetSize) {
    int len = udp.read(incomingPacket, 255);
    if (len > 0) incomingPacket[len] = 0; // Null-terminate
    receivedChar = incomingPacket[0];      // Only first character considered

    lcd.clear();

    // ===== Dangerous Signs: set buzzer =====
    switch (receivedChar) {
      case 'b':  // Pedestrian Cross
      case 'd':  // Warning
      case 'e':  // Bump Ahead
      case 'h':  // No Parking
      case 't':  // STOP
        buzzerOn = true;
        buzzerStartTime = millis();
        break;
    }

    // ===== Update LCD based on sign =====
    switch (receivedChar) {
      case 'a': lcd.print("Parking Sign"); break;
      case 'b': lcd.print("Pedestrian Cross"); break;
      case 'c': lcd.print("Round-About"); break;
      case 'd': lcd.print("Warning"); break;
      case 'e': lcd.print("Bump Ahead"); break;
      case 'f': lcd.print("Do Not Enter"); break;
      case 'g': lcd.print("No U-Turn"); break;
      case 'h': lcd.print("No Parking"); break;
      case 'i': lcd.print("No Waiting"); break;
      case 'j': userSpeed = 100; break;
      case 'k': userSpeed = 120; break;
      case 'l': userSpeed = 20;  break;
      case 'm': userSpeed = 30;  break;
      case 'n': userSpeed = 40;  break;
      case 'o': userSpeed = 50;  break;
      case 'p': userSpeed = 60;  break;
      case 'q': userSpeed = 70;  break;
      case 'r': userSpeed = 80;  break;
      case 's': userSpeed = 90;  break;
      case 't': lcd.print("STOP"); userSpeed = 0; break;
      case 'u': lcd.print("U-Turn Allowed"); break;
    }

    // ===== Display Motor Speed if applicable =====
    if (userSpeed > 0) {
      motorSpeed = map(userSpeed, 10, 120, 70, 1023);
      analogWrite(motorPinPWM, motorSpeed);
      digitalWrite(motorPinDir, LOW); // Forward
      lcd.setCursor(0,1);
      lcd.print("Speed: ");
      lcd.print(userSpeed);
      lcd.print(" km/h");
    } else {
      analogWrite(motorPinPWM, 0); // Stop motor
    }
  }

  // ===== Non-blocking Buzzer Handling =====
  if (buzzerOn) {
    digitalWrite(Buzzer, HIGH);
    if (millis() - buzzerStartTime >= buzzerDuration) {
      buzzerOn = false;
      digitalWrite(Buzzer, LOW);
    }
  }
}