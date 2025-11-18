/*
 * UNIVERSAL VERSION - Train Control Firmware with EEPROM Configuration
 * Supports PID Control + Step Response + Deadband Calibration
 *
 * UNIVERSAL CONFIGURATION:
 * - One firmware for all trains and all networks
 * - Configure via serial commands (SET_TRAIN, SET_BROKER, SET_WIFI)
 * - Stores train_id, udp_port, mqtt_broker, and wifi credentials in EEPROM
 * - Dynamic MQTT topic generation
 * - LED status feedback
 * - No hardcoded credentials - fully configurable
 *
 * CONFIGURATION COMMANDS:
 * - SET_TRAIN:trainID:port       - Configure ESP32 (e.g., SET_TRAIN:trainA:5555)
 * - SET_BROKER:ip                - Set MQTT broker IP (e.g., SET_BROKER:192.168.1.100)
 * - SET_WIFI:ssid:password       - Set WiFi credentials (e.g., SET_WIFI:MyNetwork:MyPassword)
 * - GET_TRAIN                    - Display current configuration
 * - GET_BROKER                   - Display MQTT broker IP
 * - GET_WIFI                     - Display WiFi credentials
 * - RESET_TRAIN                  - Clear configuration and restart
 * - STATUS                       - Show connection status
 *
 * LED FEEDBACK:
 * - Fast blink (200ms)  : Not configured, waiting for setup
 * - Slow blink (1s)     : Configured, attempting to connect
 * - Solid ON            : Connected to WiFi and MQTT, operational
 * - 3 quick flashes     : Configuration saved successfully
 *
 * MQTT Topics (dynamically generated):
 * - {mqtt_prefix}/sync              -> Start PID experiment
 * - {mqtt_prefix}/carroD/p          -> PID Kp parameter
 * - {mqtt_prefix}/step/sync         -> Start Step Response
 * - {mqtt_prefix}/deadband/sync     -> Start Deadband Calibration
 *
 * Example: If train_id = "trainA", mqtt_prefix = "trenes/trainA"
 */

#include <PID_v1_bc.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <VL53L0X.h>
#include <esp_wifi.h>
#include <Preferences.h>  // NEW: For EEPROM configuration storage

// =============================================================================
// EEPROM Configuration Storage (NEW)
// =============================================================================
Preferences preferences;

// Configuration variables (loaded from EEPROM)
String train_id = "";           // e.g., "trainA", "trainB", "trainC"
int configured_udp_port = 5555; // Dynamic UDP port
String configured_mqtt_broker = "192.168.137.1"; // MQTT broker IP (configurable)
String configured_wifi_ssid = "TICS322";         // WiFi SSID (configurable)
String configured_wifi_password = "esp32esp32";  // WiFi password (configurable)
bool is_configured = false;     // Configuration flag
bool wifi_configured = false;   // WiFi credentials configured flag
String mqtt_prefix = "";        // e.g., "trenes/trainA"

// LED pin for status feedback
#define STATUS_LED 2  // Built-in LED on ESP32

// Configuration mode variables
unsigned long last_led_toggle = 0;
int led_blink_interval = 200;  // Fast blink in config mode
bool led_state = false;

// =============================================================================
// Experiment Mode Selection
// =============================================================================
#define PID_MODE 0
#define STEP_MODE 1
#define DEADBAND_MODE 2

int currentExperimentMode = PID_MODE;
bool experimentActive = false;

// =============================================================================
// Network Configuration
// =============================================================================
// Note: WiFi credentials and MQTT broker are now configurable via serial
// Default values used if not configured
const int localUDPPort = 1111;

// =============================================================================
// MQTT Client Setup
// =============================================================================
WiFiClient espClient;
PubSubClient client(espClient);
WiFiUDP udp;

String carro = "carro" + String(random(100));
char msg[128];
char paquete_entrante[64];

// =============================================================================
// Motor Configuration
// =============================================================================
const int STBY = 7;
const int Control_fwd = 8;
const int Control_back = 18;
const int Control_v = 17;
int MotorSpeed = 0;

// Separate direction variables for each mode
int PIDMotorDirection = 1;
int StepMotorDirection = 1;
int DeadbandMotorDirection = 1;
int MotorDirection = 1;

// =============================================================================
// ToF Sensor
// =============================================================================
VL53L0X SensorToF;
double medi = 0;
double distancia = 25;
double old_d = 0;

// Moving average filter
int arrNumbers[3] = {0};
int pos = 0;
float newAvg = 0;
float oldAvg = 0;
int newSum = 0;
long sum = 0;
int len = sizeof(arrNumbers) / sizeof(int);

// =============================================================================
// PID Mode Variables
// =============================================================================
double x_ref = 10;
double error_distancia = 0;
double u_distancia = 0;
double rf = 0;
double Kp = 0, Ki = 0, Kd = 0;
int SampleTime = 50;
int umin = -1024, umax = 1024;
int t_envio = 50;
double etha = 0.5;
int deadband = 300;
int lim = 10;
double ponderado = 0;
bool flag_pid = true;
uint32_t tiempo_inicial_pid = 0;
bool pid_params_changed = false;

PID myPID(&error_distancia, &u_distancia, &rf, Kp, Ki, Kd, DIRECT);

// =============================================================================
// Step Response Mode Variables
// =============================================================================
double v_batt = 8.4;
double StepAmplitude = 0;
uint32_t StepTime = 0;
uint32_t delta = 0;
uint32_t tiempo_inicial_step = 0;
bool flag_step = true;
double u_step;
int stepSampleCounter = 0;
const int STEP_DELAY_SAMPLES = 2;
double appliedStepValue = 0.0;

// =============================================================================
// Deadband Calibration Mode Variables
// =============================================================================
bool flag_deadband = true;
uint32_t tiempo_inicial_deadband = 0;
int calibrated_deadband = 0;
double initial_distance = 0;
int pwm_increment = 1;
int pwm_delay = 40;
double motion_threshold = 0.08;
int max_pwm_test = 800;
bool motion_detected = false;
int Frequency = 100;

// =============================================================================
// Configuration Mode Functions (NEW)
// =============================================================================

void loadConfiguration() {
  preferences.begin("train-config", false);

  is_configured = preferences.getBool("configured", false);
  wifi_configured = preferences.getBool("wifi_configured", false);

  // Load WiFi credentials (always load, even if not fully configured)
  configured_wifi_ssid = preferences.getString("wifi_ssid", "TICS322");
  configured_wifi_password = preferences.getString("wifi_password", "esp32esp32");

  if (is_configured) {
    train_id = preferences.getString("train_id", "");
    configured_udp_port = preferences.getInt("udp_port", 5555);
    configured_mqtt_broker = preferences.getString("mqtt_broker", "192.168.137.1");

    // Generate MQTT prefix
    mqtt_prefix = "trenes/" + train_id;

    Serial.println("Configuration loaded from EEPROM:");
    Serial.println("  Train ID: " + train_id);
    Serial.println("  UDP Port: " + String(configured_udp_port));
    Serial.println("  MQTT Broker: " + configured_mqtt_broker);
    Serial.println("  WiFi SSID: " + configured_wifi_ssid);
    Serial.println("  WiFi Configured: " + String(wifi_configured ? "YES" : "NO (using defaults)"));
    Serial.println("  MQTT Prefix: " + mqtt_prefix);
  } else {
    // Load broker IP even if not configured (can be set independently)
    configured_mqtt_broker = preferences.getString("mqtt_broker", "192.168.137.1");
  }

  preferences.end();
}

void saveConfiguration(String id, int port) {
  preferences.begin("train-config", false);

  preferences.putString("train_id", id);
  preferences.putInt("udp_port", port);
  preferences.putBool("configured", true);

  preferences.end();

  Serial.println("\nConfiguration saved to EEPROM!");
  Serial.println("  Train ID: " + id);
  Serial.println("  UDP Port: " + String(port));
  Serial.println("  MQTT Broker: " + configured_mqtt_broker);

  // Flash LED 3 times to indicate success
  blinkLED(3, 150);

  Serial.println("\nRebooting...");
  delay(1000);
  ESP.restart();
}

void saveBrokerIP(String broker_ip) {
  preferences.begin("train-config", false);
  preferences.putString("mqtt_broker", broker_ip);
  preferences.end();

  configured_mqtt_broker = broker_ip;

  Serial.println("\nMQTT Broker IP saved to EEPROM!");
  Serial.println("  Broker: " + broker_ip);

  // Flash LED 3 times to indicate success
  blinkLED(3, 150);

  Serial.println("\nRestarting to apply changes...");
  delay(1000);
  ESP.restart();
}

void saveWiFiCredentials(String ssid, String password) {
  preferences.begin("train-config", false);
  preferences.putString("wifi_ssid", ssid);
  preferences.putString("wifi_password", password);
  preferences.putBool("wifi_configured", true);
  preferences.end();

  configured_wifi_ssid = ssid;
  configured_wifi_password = password;
  wifi_configured = true;

  Serial.println("\nWiFi credentials saved to EEPROM!");
  Serial.println("  SSID: " + ssid);
  Serial.println("  Password: " + String(password.length()) + " characters");

  // Flash LED 3 times to indicate success
  blinkLED(3, 150);

  Serial.println("\nRestarting to connect to WiFi...");
  delay(1000);
  ESP.restart();
}

void resetConfiguration() {
  preferences.begin("train-config", false);
  preferences.clear();
  preferences.end();

  Serial.println("\nConfiguration cleared!");
  Serial.println("Rebooting to config mode...");
  delay(1000);
  ESP.restart();
}

void printConfiguration() {
  Serial.println("\n========================================");
  Serial.println("CURRENT CONFIGURATION");
  Serial.println("========================================");

  if (is_configured) {
    Serial.println("Status: CONFIGURED");
    Serial.println("Train ID: " + train_id);
    Serial.println("UDP Port: " + String(configured_udp_port));
    Serial.println("MQTT Broker: " + configured_mqtt_broker);
    Serial.println("MQTT Prefix: " + mqtt_prefix);
    Serial.println("WiFi SSID: " + configured_wifi_ssid);
    Serial.println("WiFi Configured: " + String(wifi_configured ? "YES" : "NO (using defaults)"));

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("WiFi: CONNECTED");
      Serial.println("IP Address: " + WiFi.localIP().toString());
    } else {
      Serial.println("WiFi: DISCONNECTED");
    }

    if (client.connected()) {
      Serial.println("MQTT: CONNECTED");
    } else {
      Serial.println("MQTT: DISCONNECTED");
    }
  } else {
    Serial.println("Status: NOT CONFIGURED");
    Serial.println("Use: SET_TRAIN:trainID:port");
  }

  Serial.println("========================================\n");
}

void printBrokerIP() {
  Serial.println("\n========================================");
  Serial.println("MQTT BROKER CONFIGURATION");
  Serial.println("========================================");
  Serial.println("Broker IP: " + configured_mqtt_broker);
  Serial.println("========================================\n");
}

void printWiFi() {
  Serial.println("\n========================================");
  Serial.println("WIFI CONFIGURATION");
  Serial.println("========================================");
  Serial.println("SSID: " + configured_wifi_ssid);
  Serial.println("Password: " + String(configured_wifi_password.length()) + " characters");
  Serial.println("Configured: " + String(wifi_configured ? "YES" : "NO (using defaults)"));
  Serial.println("========================================\n");
}

void blinkLED(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(STATUS_LED, HIGH);
    delay(delayMs);
    digitalWrite(STATUS_LED, LOW);
    delay(delayMs);
  }
}

void checkSerialConfig() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.startsWith("SET_TRAIN:")) {
      // Parse: SET_TRAIN:trainA:5555
      int firstColon = command.indexOf(':');
      int secondColon = command.indexOf(':', firstColon + 1);

      if (secondColon > 0) {
        String id = command.substring(firstColon + 1, secondColon);
        String portStr = command.substring(secondColon + 1);
        int port = portStr.toInt();

        if (id.length() > 0 && port > 0) {
          Serial.println("\nConfiguring train...");
          Serial.println("  Train ID: " + id);
          Serial.println("  UDP Port: " + String(port));

          saveConfiguration(id, port);
        } else {
          Serial.println("ERROR: Invalid train ID or port");
          Serial.println("Usage: SET_TRAIN:trainA:5555");
        }
      } else {
        Serial.println("ERROR: Invalid format");
        Serial.println("Usage: SET_TRAIN:trainA:5555");
      }
    }
    else if (command == "GET_TRAIN") {
      printConfiguration();
    }
    else if (command == "RESET_TRAIN") {
      Serial.println("Resetting configuration...");
      resetConfiguration();
    }
    else if (command.startsWith("SET_BROKER:")) {
      // Parse: SET_BROKER:192.168.1.100
      int firstColon = command.indexOf(':');

      if (firstColon > 0) {
        String broker_ip = command.substring(firstColon + 1);
        broker_ip.trim();

        // Basic validation: check if it looks like an IP address
        if (broker_ip.length() >= 7 && broker_ip.indexOf('.') > 0) {
          Serial.println("\nSetting MQTT broker IP...");
          Serial.println("  Broker IP: " + broker_ip);

          saveBrokerIP(broker_ip);
        } else {
          Serial.println("ERROR: Invalid IP address format");
          Serial.println("Usage: SET_BROKER:192.168.1.100");
        }
      } else {
        Serial.println("ERROR: Invalid format");
        Serial.println("Usage: SET_BROKER:192.168.1.100");
      }
    }
    else if (command == "GET_BROKER") {
      printBrokerIP();
    }
    else if (command.startsWith("SET_WIFI:")) {
      // Parse: SET_WIFI:MySSID:MyPassword
      int firstColon = command.indexOf(':');
      int secondColon = command.indexOf(':', firstColon + 1);

      if (secondColon > 0) {
        String ssid = command.substring(firstColon + 1, secondColon);
        String password = command.substring(secondColon + 1);

        if (ssid.length() > 0) {
          Serial.println("\nSetting WiFi credentials...");
          Serial.println("  SSID: " + ssid);
          Serial.println("  Password: " + String(password.length()) + " characters");

          saveWiFiCredentials(ssid, password);
        } else {
          Serial.println("ERROR: Invalid SSID");
          Serial.println("Usage: SET_WIFI:MyNetwork:MyPassword");
        }
      } else {
        Serial.println("ERROR: Invalid format");
        Serial.println("Usage: SET_WIFI:MyNetwork:MyPassword");
      }
    }
    else if (command == "GET_WIFI") {
      printWiFi();
    }
    else if (command == "STATUS") {
      printConfiguration();
    }
    else {
      Serial.println("Unknown command: " + command);
      Serial.println("Available commands:");
      Serial.println("  SET_TRAIN:trainID:port - Configure ESP32");
      Serial.println("  SET_BROKER:ip          - Set MQTT broker IP");
      Serial.println("  SET_WIFI:ssid:password - Set WiFi credentials");
      Serial.println("  GET_TRAIN              - Show configuration");
      Serial.println("  GET_BROKER             - Show broker IP");
      Serial.println("  GET_WIFI               - Show WiFi credentials");
      Serial.println("  RESET_TRAIN            - Clear configuration");
      Serial.println("  STATUS                 - Show status");
    }
  }
}

void enterConfigMode() {
  Serial.println("\n========================================");
  Serial.println("CONFIGURATION MODE");
  Serial.println("========================================");
  Serial.println("Commands:");
  Serial.println("  SET_TRAIN:trainA:5555          - Configure ESP32");
  Serial.println("  SET_BROKER:192.168.1.100       - Set MQTT broker IP");
  Serial.println("  SET_WIFI:MySSID:MyPassword     - Set WiFi credentials");
  Serial.println("  GET_TRAIN                      - Show configuration");
  Serial.println("  GET_BROKER                     - Show broker IP");
  Serial.println("  GET_WIFI                       - Show WiFi credentials");
  Serial.println("  RESET_TRAIN                    - Clear configuration");
  Serial.println("========================================");
  Serial.println("Waiting for configuration...");
  Serial.println("(LED will blink fast until configured)\n");

  // Wait in config mode until configured
  while (!is_configured) {
    // Fast blink LED
    if (millis() - last_led_toggle > led_blink_interval) {
      led_state = !led_state;
      digitalWrite(STATUS_LED, led_state ? HIGH : LOW);
      last_led_toggle = millis();
    }

    checkSerialConfig();
    delay(10);
  }
}

void updateStatusLED() {
  // Update LED based on connection status
  if (!is_configured) {
    // Fast blink - not configured
    if (millis() - last_led_toggle > 200) {
      led_state = !led_state;
      digitalWrite(STATUS_LED, led_state ? HIGH : LOW);
      last_led_toggle = millis();
    }
  }
  else if (!client.connected()) {
    // Slow blink - trying to connect
    if (millis() - last_led_toggle > 1000) {
      led_state = !led_state;
      digitalWrite(STATUS_LED, led_state ? HIGH : LOW);
      last_led_toggle = millis();
    }
  }
  else {
    // Solid on - connected and operational
    digitalWrite(STATUS_LED, HIGH);
  }
}

// =============================================================================
// Setup
// =============================================================================
void setup() {
  Serial.begin(115200);
  pinMode(STATUS_LED, OUTPUT);

  Serial.println("\n\n");
  Serial.println("==============================================");
  Serial.println("  UNIVERSAL Train Control Firmware");
  Serial.println("  Version: 1.0 - EEPROM Configuration");
  Serial.println("  Modes: PID + Step Response + Deadband Cal");
  Serial.println("==============================================");

  // Load configuration from EEPROM
  loadConfiguration();

  if (!is_configured) {
    Serial.println("\n*** TRAIN NOT CONFIGURED ***");
    enterConfigMode();
  }

  // If we reach here, train is configured
  Serial.println("\n========================================");
  Serial.println("TRAIN CONFIGURATION LOADED");
  Serial.println("========================================");
  Serial.println("Train ID: " + train_id);
  Serial.println("UDP Port: " + String(configured_udp_port));
  Serial.println("MQTT Prefix: " + mqtt_prefix);
  Serial.println("========================================\n");

  // WiFi Setup
  setup_wifi();

  // MQTT Setup - Use configured broker IP
  Serial.println("Connecting to MQTT broker: " + configured_mqtt_broker);
  client.setServer(configured_mqtt_broker.c_str(), 1883);
  client.setCallback(mqtt_callback);
  reconnect_mqtt();

  // Motor Setup
  setup_motor();

  // ToF Sensor Setup
  setup_ToF();

  // PID Configuration
  myPID.SetSampleTime(SampleTime);
  myPID.SetOutputLimits(umin, umax);
  myPID.SetTunings(Kp, Ki, Kd);
  myPID.SetMode(MANUAL);

  Serial.println("PID Configuration:");
  Serial.print("  Sample Time: "); Serial.print(SampleTime); Serial.println("ms");
  Serial.print("  Output Limits: ±"); Serial.println(umax);
  Serial.print("  Deadband Default: "); Serial.println(deadband);

  Serial.println("==============================================");
  Serial.println("Setup Complete! Ready for experiments.");
  Serial.println("Available experiments:");
  Serial.println("  - PID Control: " + mqtt_prefix + "/sync");
  Serial.println("  - Step Response: " + mqtt_prefix + "/step/sync");
  Serial.println("  - Deadband Cal: " + mqtt_prefix + "/deadband/sync");
  Serial.println("==============================================");

  // Solid LED on when ready
  digitalWrite(STATUS_LED, HIGH);
}

// =============================================================================
// Main Loop
// =============================================================================
void loop() {
  // Always check for serial config commands
  checkSerialConfig();

  // Update status LED
  updateStatusLED();

  // Maintain MQTT connection
  if (!client.connected()) {
    reconnect_mqtt();
  }
  client.loop();

  // Run appropriate experiment loop
  if (experimentActive) {
    switch (currentExperimentMode) {
      case PID_MODE:
        loop_pid_experiment();
        break;
      case STEP_MODE:
        loop_step_experiment();
        break;
      case DEADBAND_MODE:
        loop_deadband_experiment();
        break;
    }
  } else {
    // Idle mode - motor off
    MotorSpeed = 0;
    SetMotorControl();
    delay(100);
  }
}

// =============================================================================
// PID Experiment Loop
// =============================================================================
void loop_pid_experiment() {
  if (flag_pid == false) {
    flag_pid = true;
    tiempo_inicial_pid = millis();
    Serial.println("[PID] Experiment started!");
    myPID.SetMode(AUTOMATIC);
    PIDMotorDirection = 1;
  }

  if (pid_params_changed) {
    myPID.SetTunings(Kp, Ki, Kd);
    pid_params_changed = false;
    Serial.print("[PID] Parameters updated - Kp:");
    Serial.print(Kp); Serial.print(", Ki:");
    Serial.print(Ki); Serial.print(", Kd:");
    Serial.println(Kd);
  }

  read_ToF_sensor();
  distancia = medi;
  error_distancia = x_ref - distancia;
  myPID.Compute();
  double u = u_distancia;

  if (distancia > 200) {
    if (MotorSpeed < 200) {
      MotorSpeed = MotorSpeed - 10;
    } else {
      MotorSpeed = 0;
    }
    SetMotorControl();
    send_udp_pid_data();
    delay(SampleTime);
    return;
  }

  if (abs(u) <= lim) {
    MotorSpeed = 0;
  }
  else if (u > lim) {
    PIDMotorDirection = 1;
    int deadband_comp = deadband;
    MotorSpeed = constrain(int(u + deadband_comp), 0, 1024);
  }
  else if (u < -lim) {
    PIDMotorDirection = 0;
    int deadband_comp = deadband;
    MotorSpeed = constrain(int(-u + deadband_comp), 0, 1024);
  }

  if ((abs(u) <= lim) && (abs(ponderado) <= 0.75)) {
    MotorSpeed = 0;
  }

  MotorDirection = PIDMotorDirection;
  SetMotorControl();
  send_udp_pid_data();
  delay(SampleTime);
}

// =============================================================================
// Step Response Experiment Loop
// =============================================================================
void loop_step_experiment() {
  if (flag_step == false) {
    flag_step = true;
    Serial.println("[STEP] Experiment started!");
    Serial.print("  Amplitude: "); Serial.print(StepAmplitude); Serial.println("V");
    Serial.print("  Duration: "); Serial.print(StepTime / 1000.0); Serial.println("s");
    Serial.print("  Direction: "); Serial.println(StepMotorDirection ? "Forward" : "Reverse");

    delta = millis() - tiempo_inicial_step;
    StepTime = StepTime + millis();

    stepSampleCounter = 0;
    appliedStepValue = 0.0;
    Serial.print("  Waiting for "); Serial.print(STEP_DELAY_SAMPLES); Serial.println(" baseline samples before applying step...");
  }

  read_ToF_sensor();

  if (stepSampleCounter < STEP_DELAY_SAMPLES) {
    appliedStepValue = 0.0;
    MotorSpeed = 0;
    stepSampleCounter++;
    if (stepSampleCounter == STEP_DELAY_SAMPLES) {
      Serial.println("[STEP] Baseline samples collected, applying step now!");
    }
  } else {
    appliedStepValue = StepAmplitude;
    u_step = StepAmplitude * 1024 / v_batt;
    MotorSpeed = constrain(u_step, 0, 1024);
  }

  MotorDirection = StepMotorDirection;
  SetMotorControl();
  send_udp_step_data();

  if (millis() >= StepTime) {
    Serial.println("[STEP] Experiment duration complete");
    flag_step = true;
    StepTime = 0;
    StepAmplitude = 0;
    experimentActive = false;
    MotorSpeed = 0;
    SetMotorControl();
  }

  delay(21);
}

// =============================================================================
// Deadband Calibration Experiment Loop
// =============================================================================
void loop_deadband_experiment() {
  if (flag_deadband == false) {
    flag_deadband = true;
    tiempo_inicial_deadband = millis();
    Serial.println("[DEADBAND] Calibration started!");
    Serial.print("  Direction: "); Serial.println(DeadbandMotorDirection ? "Forward" : "Reverse");
    Serial.print("  Motion threshold: "); Serial.print(motion_threshold); Serial.println(" cm");

    double sum = 0;
    for (int i = 0; i < 10; i++) {
      read_ToF_sensor();
      sum += medi;
      delay(20);
    }
    initial_distance = sum / 10.0;

    MotorSpeed = 0;
    calibrated_deadband = 0;
    motion_detected = false;

    ledcAttach(Control_v, Frequency, 10);

    Serial.print("  Initial distance (averaged): "); Serial.print(initial_distance); Serial.println(" cm");
    Serial.println("  Increasing PWM from 0 until motion detected...");
  }

  MotorSpeed += pwm_increment;
  MotorDirection = DeadbandMotorDirection;
  SetMotorControl();

  double sum = 0;
  for (int i = 0; i < 3; i++) {
    read_ToF_sensor();
    sum += medi;
    delay(5);
  }
  double current_distance = sum / 3.0;
  double distance_change = abs(current_distance - initial_distance);

  send_udp_deadband_data();

  if (distance_change >= motion_threshold && MotorSpeed > 50) {
    motion_detected = true;
    calibrated_deadband = MotorSpeed;

    Serial.println("========================================");
    Serial.println("✓ MOTION DETECTED!");
    Serial.print("  Deadband PWM: "); Serial.println(calibrated_deadband);
    Serial.print("  Initial distance: "); Serial.print(initial_distance); Serial.println(" cm");
    Serial.print("  Final distance: "); Serial.print(current_distance); Serial.println(" cm");
    Serial.print("  Distance moved: "); Serial.print(distance_change); Serial.println(" cm");
    Serial.println("========================================");

    send_udp_deadband_data();
    delay(50);

    MotorSpeed = 0;
    SetMotorControl();

    // Publish result with dynamic topic
    String result_topic = mqtt_prefix + "/deadband/result";
    client.publish(result_topic.c_str(), String(calibrated_deadband).c_str());

    delay(1000);
    experimentActive = false;
    flag_deadband = true;

    return;
  }

  if (MotorSpeed % 50 == 0) {
    Serial.print("  PWM: "); Serial.print(MotorSpeed);
    Serial.print(" - Distance: "); Serial.print(current_distance);
    Serial.print(" cm (change: "); Serial.print(distance_change);
    Serial.println(" cm)");
  }

  delay(pwm_delay);

  if (MotorSpeed >= max_pwm_test) {
    Serial.println("========================================");
    Serial.println("⚠ WARNING: Reached maximum PWM without motion!");
    Serial.println("========================================");

    calibrated_deadband = deadband;
    MotorSpeed = 0;
    SetMotorControl();

    String result_topic = mqtt_prefix + "/deadband/result";
    String error_topic = mqtt_prefix + "/deadband/error";
    client.publish(result_topic.c_str(), String(calibrated_deadband).c_str());
    client.publish(error_topic.c_str(), "Timeout - no motion detected");

    experimentActive = false;
    flag_deadband = true;
  }
}

// =============================================================================
// MQTT Callback (MODIFIED - Dynamic Topics)
// =============================================================================
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  String mensaje = "";
  for (unsigned int i = 0; i < length; i++) {
    mensaje += (char)payload[i];
  }

  String topic_str = String(topic);
  Serial.print("[MQTT] "); Serial.print(topic_str); Serial.print(" = "); Serial.println(mensaje);

  // =========================================================================
  // PID Control Topics (DYNAMIC)
  // =========================================================================
  if (topic_str == mqtt_prefix + "/sync") {
    if (mensaje == "True") {
      currentExperimentMode = PID_MODE;
      experimentActive = true;
      flag_pid = false;
      tiempo_inicial_pid = millis();
      PIDMotorDirection = 1;
      Serial.println("[MODE] Switched to PID Control");
    } else {
      experimentActive = false;
      flag_pid = true;
      myPID.SetMode(MANUAL);
      u_distancia = 0;
      error_distancia = 0;
      MotorSpeed = 0;
      PIDMotorDirection = 1;
      MotorDirection = PIDMotorDirection;
      SetMotorControl();
      Serial.println("[PID] Stopped");
    }
  }
  else if (currentExperimentMode != STEP_MODE && currentExperimentMode != DEADBAND_MODE) {
    if (topic_str == mqtt_prefix + "/carroD/p") {
      double new_Kp = mensaje.toFloat();
      if (new_Kp != Kp) {
        Kp = new_Kp;
        pid_params_changed = true;
        client.publish((mqtt_prefix + "/carroD/p/status").c_str(), String(Kp).c_str());
      }
    }
    else if (topic_str == mqtt_prefix + "/carroD/i") {
      double new_Ki = mensaje.toFloat();
      if (new_Ki != Ki) {
        Ki = new_Ki;
        pid_params_changed = true;
        client.publish((mqtt_prefix + "/carroD/i/status").c_str(), String(Ki).c_str());
      }
    }
    else if (topic_str == mqtt_prefix + "/carroD/d") {
      double new_Kd = mensaje.toFloat();
      if (new_Kd != Kd) {
        Kd = new_Kd;
        pid_params_changed = true;
        client.publish((mqtt_prefix + "/carroD/d/status").c_str(), String(Kd).c_str());
      }
    }
    else if (topic_str == mqtt_prefix + "/ref") {
      double new_ref = mensaje.toFloat();
      if (new_ref != x_ref) {
        x_ref = new_ref;
        client.publish((mqtt_prefix + "/carroD/ref/status").c_str(), String(x_ref).c_str());
      }
    }
    else if (topic_str == mqtt_prefix + "/carroD/request_params") {
      client.publish((mqtt_prefix + "/carroD/p/status").c_str(), String(Kp).c_str());
      client.publish((mqtt_prefix + "/carroD/i/status").c_str(), String(Ki).c_str());
      client.publish((mqtt_prefix + "/carroD/d/status").c_str(), String(Kd).c_str());
      client.publish((mqtt_prefix + "/carroD/ref/status").c_str(), String(x_ref).c_str());
    }
  }

  // =========================================================================
  // Step Response Topics (DYNAMIC)
  // =========================================================================
  if (topic_str == mqtt_prefix + "/step/sync") {
    if (mensaje == "True" && StepTime > 0 && StepAmplitude > 0) {
      currentExperimentMode = STEP_MODE;
      experimentActive = true;
      flag_step = false;
      tiempo_inicial_step = millis();
      Serial.println("[MODE] Switched to Step Response");
    } else {
      experimentActive = false;
      flag_step = true;
      MotorSpeed = 0;
      StepMotorDirection = 1;
      MotorDirection = StepMotorDirection;
      SetMotorControl();
      Serial.println("[STEP] Stopped");
    }
  }
  if (topic_str == mqtt_prefix + "/step/amplitude") {
    StepAmplitude = mensaje.toFloat();
    StepAmplitude = constrain(StepAmplitude, 0.0, v_batt);
    client.publish((mqtt_prefix + "/step/amplitude/status").c_str(), String(StepAmplitude, 1).c_str());
  }
  else if (topic_str == mqtt_prefix + "/step/time") {
    float time_seconds = mensaje.toFloat();
    StepTime = time_seconds * 1000;
    StepTime = constrain(StepTime, 0, 20000);
    client.publish((mqtt_prefix + "/step/time/status").c_str(), String(time_seconds, 1).c_str());
  }
  else if (topic_str == mqtt_prefix + "/step/direction") {
    StepMotorDirection = mensaje.toInt();
    StepMotorDirection = constrain(StepMotorDirection, 0, 1);
    client.publish((mqtt_prefix + "/step/direction/status").c_str(), String(StepMotorDirection).c_str());
  }
  else if (topic_str == mqtt_prefix + "/step/vbatt") {
    v_batt = mensaje.toFloat();
    v_batt = constrain(v_batt, 0.0, 8.4);
    client.publish((mqtt_prefix + "/step/vbatt/status").c_str(), String(v_batt, 1).c_str());
  }
  else if (topic_str == mqtt_prefix + "/step/request_params") {
    client.publish((mqtt_prefix + "/step/amplitude/status").c_str(), String(StepAmplitude, 1).c_str());
    client.publish((mqtt_prefix + "/step/time/status").c_str(), String(StepTime / 1000.0, 1).c_str());
    client.publish((mqtt_prefix + "/step/direction/status").c_str(), String(StepMotorDirection).c_str());
    client.publish((mqtt_prefix + "/step/vbatt/status").c_str(), String(v_batt, 1).c_str());
  }

  // =========================================================================
  // Deadband Calibration Topics (DYNAMIC)
  // =========================================================================
  if (topic_str == mqtt_prefix + "/deadband/sync") {
    if (mensaje == "True") {
      currentExperimentMode = DEADBAND_MODE;
      experimentActive = true;
      flag_deadband = false;
      tiempo_inicial_deadband = millis();
      Serial.println("[MODE] Switched to Deadband Calibration");
    } else {
      experimentActive = false;
      flag_deadband = true;
      MotorSpeed = 0;
      DeadbandMotorDirection = 1;
      MotorDirection = DeadbandMotorDirection;
      SetMotorControl();
      Serial.println("[DEADBAND] Stopped");
    }
  }
  else if (topic_str == mqtt_prefix + "/deadband/direction") {
    DeadbandMotorDirection = mensaje.toInt();
    DeadbandMotorDirection = constrain(DeadbandMotorDirection, 0, 1);
    client.publish((mqtt_prefix + "/deadband/direction/status").c_str(), String(DeadbandMotorDirection).c_str());
  }
  else if (topic_str == mqtt_prefix + "/deadband/threshold") {
    motion_threshold = mensaje.toFloat();
    motion_threshold = constrain(motion_threshold, 0.01, 1.0);
    client.publish((mqtt_prefix + "/deadband/threshold/status").c_str(), String(motion_threshold, 2).c_str());
  }
  else if (topic_str == mqtt_prefix + "/deadband/request_params") {
    client.publish((mqtt_prefix + "/deadband/direction/status").c_str(), String(DeadbandMotorDirection).c_str());
    client.publish((mqtt_prefix + "/deadband/threshold/status").c_str(), String(motion_threshold, 2).c_str());
    client.publish((mqtt_prefix + "/deadband/result").c_str(), String(calibrated_deadband).c_str());
  }
  else if (topic_str == mqtt_prefix + "/deadband/apply") {
    if (mensaje == "True" && calibrated_deadband > 0) {
      deadband = calibrated_deadband;
      client.publish((mqtt_prefix + "/deadband/applied").c_str(), String(deadband).c_str());
      Serial.print("[DEADBAND] Applied to PID mode: "); Serial.println(deadband);
    }
  }
}

// =============================================================================
// WiFi Setup
// =============================================================================
void setup_wifi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(configured_wifi_ssid);

  WiFi.mode(WIFI_STA);
  esp_wifi_set_ps(WIFI_PS_NONE);
  WiFi.begin(configured_wifi_ssid.c_str(), configured_wifi_password.c_str());

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  udp.begin(localUDPPort);
  Serial.print("UDP listening on port ");
  Serial.println(localUDPPort);
}

// =============================================================================
// MQTT Reconnect (MODIFIED - Dynamic Topics)
// =============================================================================
void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");

    if (client.connect(carro.c_str())) {
      Serial.println(" connected!");

      // Subscribe to PID topics (DYNAMIC)
      client.subscribe((mqtt_prefix + "/sync").c_str());
      client.subscribe((mqtt_prefix + "/carroD/p").c_str());
      client.subscribe((mqtt_prefix + "/carroD/i").c_str());
      client.subscribe((mqtt_prefix + "/carroD/d").c_str());
      client.subscribe((mqtt_prefix + "/ref").c_str());
      client.subscribe((mqtt_prefix + "/carroD/request_params").c_str());

      // Subscribe to Step Response topics (DYNAMIC)
      client.subscribe((mqtt_prefix + "/step/sync").c_str());
      client.subscribe((mqtt_prefix + "/step/amplitude").c_str());
      client.subscribe((mqtt_prefix + "/step/time").c_str());
      client.subscribe((mqtt_prefix + "/step/direction").c_str());
      client.subscribe((mqtt_prefix + "/step/vbatt").c_str());
      client.subscribe((mqtt_prefix + "/step/request_params").c_str());

      // Subscribe to Deadband Calibration topics (DYNAMIC)
      client.subscribe((mqtt_prefix + "/deadband/sync").c_str());
      client.subscribe((mqtt_prefix + "/deadband/direction").c_str());
      client.subscribe((mqtt_prefix + "/deadband/threshold").c_str());
      client.subscribe((mqtt_prefix + "/deadband/request_params").c_str());
      client.subscribe((mqtt_prefix + "/deadband/apply").c_str());

      Serial.println("Subscribed to all topics with prefix: " + mqtt_prefix);
    } else {
      Serial.print(" failed, rc=");
      Serial.print(client.state());
      Serial.println(" - retrying in 5 seconds");
      delay(5000);
    }
  }
}

// =============================================================================
// UDP Data Sending (MODIFIED - Dynamic Port)
// =============================================================================
void send_udp_pid_data() {
  uint32_t time_now = millis();
  double u = u_distancia;
  String cadena = String(time_now) + "," +
                  String(distancia) + "," +
                  String(x_ref) + "," +
                  String(error_distancia) + "," +
                  String(Kp) + "," +
                  String(Ki) + "," +
                  String(Kd) + "," +
                  String(u);

  cadena.toCharArray(msg, cadena.length() + 1);
  udp.beginPacket(configured_mqtt_broker.c_str(), configured_udp_port);  // Use configured broker and port
  udp.print(msg);
  udp.endPacket();
}

void send_udp_step_data() {
  uint32_t time_now = millis();
  String cadena = String(delta) + "," +
                  String(time_now) + "," +
                  String(StepMotorDirection) + "," +
                  String(v_batt) + "," +
                  String(medi) + "," +
                  String(StepAmplitude) + "," +
                  String(MotorSpeed) + "," +
                  String(appliedStepValue);

  cadena.toCharArray(msg, cadena.length() + 1);
  udp.beginPacket(configured_mqtt_broker.c_str(), configured_udp_port);  // Use configured broker and port
  udp.print(msg);
  udp.endPacket();
}

void send_udp_deadband_data() {
  uint32_t time_now = millis() - tiempo_inicial_deadband;
  String cadena = String(time_now) + "," +
                  String(MotorSpeed) + "," +
                  String(medi) + "," +
                  String(initial_distance) + "," +
                  String(motion_detected ? 1 : 0);

  cadena.toCharArray(msg, cadena.length() + 1);
  udp.beginPacket(configured_mqtt_broker.c_str(), configured_udp_port);  // Use configured broker and port
  udp.print(msg);
  udp.endPacket();
}

// =============================================================================
// Sensor Reading
// =============================================================================
void read_ToF_sensor() {
  medi = 0;
  for (int i = 0; i < 2; i++) {
    uint16_t range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);
    medi += range;
    delay(21);
  }
  medi = medi / 2;

  newSum = movingSum(arrNumbers, &sum, pos, len, medi);
  newAvg = newSum / (float)len;
  pos++;
  if (pos >= len) {
    pos = 0;
  }
  oldAvg = newAvg;
  medi = (0.8 * newAvg + 0.2 * oldAvg) / 10.0;
}

int movingSum(int *ptrArrNumbers, long *ptrSum, int pos, int len, int nextNum) {
  *ptrSum = *ptrSum - ptrArrNumbers[pos] + nextNum;
  ptrArrNumbers[pos] = nextNum;
  return *ptrSum;
}

// =============================================================================
// Motor Control Functions
// =============================================================================
void setup_motor() {
  pinMode(STBY, OUTPUT);
  pinMode(Control_fwd, OUTPUT);
  pinMode(Control_back, OUTPUT);
  pinMode(Control_v, OUTPUT);

  digitalWrite(STBY, HIGH);
  digitalWrite(Control_v, HIGH);

  ledcAttach(Control_v, 100, 10);

  Serial.println("Motor initialized");
}

void SetMotorControl() {
  if (MotorDirection == 1) {
    digitalWrite(Control_fwd, LOW);
    digitalWrite(Control_back, HIGH);
  } else {
    digitalWrite(Control_fwd, HIGH);
    digitalWrite(Control_back, LOW);
  }

  int pwm_value = constrain(MotorSpeed, 0, 1024);
  ledcWrite(Control_v, pwm_value);
}

// =============================================================================
// ToF Sensor Setup
// =============================================================================
void setup_ToF() {
  Serial.println("Initializing ToF sensor...");

  Wire.begin(10, 9);

  SensorToF.setTimeout(500);
  while (!SensorToF.init()) {
    Serial.println("Failed to detect and initialize sensor!");
    delay(1000);
  }

  SensorToF.setSignalRateLimit(0.25);
  SensorToF.setMeasurementTimingBudget(22000);
  SensorToF.startContinuous();

  Serial.println("ToF sensor ready");
}
