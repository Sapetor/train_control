/*
 * Unified Train Control Firmware
 * Supports both PID Control and Step Response experiments
 * 
 * Experiment Modes:
 * - PID_MODE: Closed-loop PID control with distance tracking
 * - STEP_MODE: Open-loop step response for system identification
 * 
 * MQTT Topics automatically switch experiment mode:
 * - trenes/sync -> Starts PID experiment
 * - trenes/step/sync -> Starts Step Response experiment
 */

#include <PID_v1_bc.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <VL53L0X.h>
#include <esp_wifi.h>

// =============================================================================
// Experiment Mode Selection
// =============================================================================
#define PID_MODE 0
#define STEP_MODE 1

int currentExperimentMode = PID_MODE;  // Default to PID mode
bool experimentActive = false;

// =============================================================================
// Network Configuration
// =============================================================================
const char* ssid = "TICS322";
const char* password = "esp32esp32";
const char* mqtt_server = "192.168.137.1";
const int udpPort = 5555;
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

// FIXED: Separate direction variables for each mode to prevent interference
int PIDMotorDirection = 1;   // Direction for PID mode (1=Forward, 0=Reverse)
int StepMotorDirection = 1;  // Direction for Step mode (1=Forward, 0=Reverse)

// For backward compatibility, we'll update this based on mode
int MotorDirection = 1;  // Will be set from mode-specific variables

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
double x_ref = 10;           // Distance reference (cm)
double error_distancia;
double u_distancia;
double rf = 0;
double Kp = 0, Ki = 0, Kd = 0;
int SampleTime = 50;
int umin = -1024, umax = 1024;
int t_envio = 50;
double etha = 0.5;
int deadband = 300;
int lim = 10;  // Minimum PID output threshold
double ponderado = 0;  // Weighted error for velocity-based control
double last_distancia = 0;  // For velocity calculation
bool flag_pid = true;
uint32_t tiempo_inicial_pid = 0;

// MQTT Connection Management
unsigned long last_mqtt_attempt = 0;
const unsigned long MQTT_RECONNECT_INTERVAL = 5000;  // Try reconnect every 5 seconds
int mqtt_retry_count = 0;

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

// =============================================================================
// Setup
// =============================================================================
void setup() {
    Serial.begin(115200);
    delay(500);  // Give serial time to initialize
    Serial.println();
    Serial.println("===================================");
    Serial.println("  Unified Train Control Firmware");
    Serial.println("  Version: 2.1 (Fixed)");
    Serial.println("===================================");
    Serial.println("Supports:");
    Serial.println("  - PID Control");
    Serial.println("  - Step Response");
    Serial.println("===================================");

    // WiFi Setup
    setup_wifi();

    // MQTT Setup (non-blocking)
    client.setServer(mqtt_server, 1883);
    client.setCallback(mqtt_callback);
    initial_mqtt_connect();  // Try to connect, but don't block forever

    // Motor Setup
    setup_motor();

    // ToF Sensor Setup
    setup_ToF();

    // PID Setup
    myPID.SetMode(MANUAL);
    myPID.SetOutputLimits(umin, umax);
    myPID.SetSampleTime(SampleTime);

    Serial.println("===================================");
    Serial.println("✓ Setup Complete!");
    Serial.println("===================================");
    Serial.print("Current Mode: ");
    Serial.println(currentExperimentMode == PID_MODE ? "PID Control" : "Step Response");
    Serial.println("Waiting for experiment start via MQTT...");
    Serial.println();
}

// =============================================================================
// Main Loop
// =============================================================================
void loop() {
    // NON-BLOCKING MQTT connection maintenance
    if (!client.connected()) {
        unsigned long now = millis();
        if (now - last_mqtt_attempt > MQTT_RECONNECT_INTERVAL) {
            last_mqtt_attempt = now;
            Serial.print("[MQTT] Attempting reconnection (attempt ");
            Serial.print(mqtt_retry_count + 1);
            Serial.println(")...");
            attempt_mqtt_reconnect();  // Non-blocking single attempt
        }
    } else {
        mqtt_retry_count = 0;  // Reset counter when connected
    }

    client.loop();

    // Run appropriate experiment loop
    if (experimentActive) {
        if (currentExperimentMode == PID_MODE) {
            loop_pid_experiment();
        } else if (currentExperimentMode == STEP_MODE) {
            loop_step_experiment();
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
    // Sync message on first iteration
    if (flag_pid == false) {
        flag_pid = true;
        Serial.println("[PID] Experiment started!");
        tiempo_inicial_pid = millis();
        
        // Configure PID before enabling
        myPID.SetTunings(Kp, Ki, Kd);
        myPID.SetOutputLimits(umin, umax);
        myPID.SetSampleTime(SampleTime);
        
        // Enable PID after configuration
        myPID.SetMode(AUTOMATIC);
    }
    
    // Read sensor
    read_ToF_sensor();
    distancia = medi;

    // Calculate velocity (derivative of distance)
    double velocity = (distancia - last_distancia) * 1000.0 / SampleTime;  // cm/s
    last_distancia = distancia;

    // Calculate error
    error_distancia = x_ref - distancia;

    // Weighted error for velocity-based control (combines position error and velocity)
    ponderado = error_distancia - etha * velocity;

    // Compute PID
    myPID.Compute();
    
    double u = u_distancia;  // PID output
    
    // Safety: No object in front (distance > 200cm)
    if (distancia > 200) {
        if (MotorSpeed < 200) {
            MotorSpeed = MotorSpeed - 10;
        } else {
            MotorSpeed = 0;
        }
        myPID.SetMode(MANUAL);  // Stop integrating
        SetMotorControl();
        send_udp_pid_data();
        delay(SampleTime);
        return;
    }
    
    // Normal operation with object detected
    if (distancia < 200) {
        myPID.SetMode(AUTOMATIC);  // Revive PID
    }
    
    // Apply control logic with deadband compensation
    if (u < -lim) {
        // Reverse
        PIDMotorDirection = 0;  // FIXED: Use PID-specific direction
        MotorSpeed = int(-u + deadband);
    }
    else if (u > lim) {
        // Forward
        PIDMotorDirection = 1;  // FIXED: Use PID-specific direction
        MotorSpeed = int(u + deadband);
    }
    else {
        // FIXED: Small error zone - simplified logic
        myPID.SetMode(MANUAL);
        MotorSpeed = 0;
        // Keep last direction for smooth restart (don't change direction)
    }
    
    // Additional stop condition when at rest
    if ((u >= -lim) && (u <= lim) && (abs(ponderado) <= 0.75)) {
        MotorSpeed = 0;
        // Keep last direction (don't change)
    }
    
    // Update global MotorDirection from PID-specific variable
    MotorDirection = PIDMotorDirection;
    
    SetMotorControl();
    
    // Send data via UDP (PID format)
    send_udp_pid_data();
    
    delay(SampleTime);
}

// =============================================================================
// Step Response Experiment Loop
// =============================================================================
void loop_step_experiment() {
    // Sync message on first iteration
    if (flag_step == false) {
        flag_step = true;
        Serial.println("[STEP] Experiment started!");
        Serial.print("  Amplitude: "); Serial.print(StepAmplitude); Serial.println("V");
        Serial.print("  Duration: "); Serial.print(StepTime / 1000.0); Serial.println("s");
        Serial.print("  Direction: "); Serial.println(MotorDirection ? "Forward" : "Reverse");
        
        delta = millis() - tiempo_inicial_step;
        StepTime = StepTime + millis();
    }
    
    // Read sensor
    read_ToF_sensor();
    
    // Apply step input
    u_step = StepAmplitude * 1024 / v_batt;
    MotorSpeed = constrain(u_step, 0, 1024);
    
    // Update global MotorDirection from Step-specific variable
    MotorDirection = StepMotorDirection;
    SetMotorControl();
    
    // Send data via UDP (Step format)
    send_udp_step_data();
    
    // Check if experiment duration elapsed
    if (millis() >= StepTime) {
        Serial.println("[STEP] Experiment duration complete");
        flag_step = true;  // Reset flag for next start
        StepTime = 0;
        StepAmplitude = 0;
        experimentActive = false;
        MotorSpeed = 0;
        SetMotorControl();
    }
    
    delay(21);  // Fast sampling for step response
}

// =============================================================================
// MQTT Callback - Handles both PID and Step Response topics
// CRITICAL FIX: Removed chained else-if to allow all topics to be checked
// =============================================================================
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
    String mensaje = "";
    for (unsigned int i = 0; i < length; i++) {
        mensaje += (char)payload[i];
    }

    String topic_str = String(topic);
    Serial.print("[MQTT] "); Serial.print(topic_str); Serial.print(" = "); Serial.println(mensaje);

    // =========================================================================
    // PID Control Topics - Use SEPARATE IF statements, not else-if chain!
    // =========================================================================
    if (topic_str == "trenes/sync") {
        if (mensaje == "True") {
            currentExperimentMode = PID_MODE;
            experimentActive = true;
            flag_pid = false;
            tiempo_inicial_pid = millis();
            PIDMotorDirection = 1;
            last_distancia = 0;  // Reset velocity calculation
            Serial.println("[MODE] ✓ Switched to PID Control");
            Serial.print("[PID] Kp="); Serial.print(Kp);
            Serial.print(" Ki="); Serial.print(Ki);
            Serial.print(" Kd="); Serial.print(Kd);
            Serial.print(" Ref="); Serial.println(x_ref);
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
            Serial.println("[PID] ✗ Stopped");
        }
    }

    // PID Parameters - Only update when NOT in Step mode
    if (currentExperimentMode != STEP_MODE && topic_str == "trenes/carroD/p") {
        Kp = mensaje.toFloat();
        client.publish("trenes/carroD/p/status", String(Kp).c_str());
        Serial.print("[PID] Kp updated: "); Serial.println(Kp);
    }
    if (currentExperimentMode != STEP_MODE && topic_str == "trenes/carroD/i") {
        Ki = mensaje.toFloat();
        client.publish("trenes/carroD/i/status", String(Ki).c_str());
        Serial.print("[PID] Ki updated: "); Serial.println(Ki);
    }
    if (currentExperimentMode != STEP_MODE && topic_str == "trenes/carroD/d") {
        Kd = mensaje.toFloat();
        client.publish("trenes/carroD/d/status", String(Kd).c_str());
        Serial.print("[PID] Kd updated: "); Serial.println(Kd);
    }
    if (currentExperimentMode != STEP_MODE && topic_str == "trenes/ref") {
        x_ref = mensaje.toFloat();
        client.publish("trenes/carroD/ref/status", String(x_ref).c_str());
        Serial.print("[PID] Reference updated: "); Serial.println(x_ref);
    }
    if (currentExperimentMode != STEP_MODE && topic_str == "trenes/carroD/request_params") {
        client.publish("trenes/carroD/p/status", String(Kp).c_str());
        client.publish("trenes/carroD/i/status", String(Ki).c_str());
        client.publish("trenes/carroD/d/status", String(Kd).c_str());
        client.publish("trenes/carroD/ref/status", String(x_ref).c_str());
        Serial.println("[PID] Parameters requested - sent status");
    }

    // =========================================================================
    // Step Response Topics - SEPARATE IF statements for proper handling
    // =========================================================================
    if (topic_str == "trenes/step/sync") {
        if (mensaje == "True" && StepTime > 0 && StepAmplitude > 0) {
            currentExperimentMode = STEP_MODE;
            experimentActive = true;
            flag_step = false;
            tiempo_inicial_step = millis();
            Serial.println("[MODE] ✓ Switched to Step Response");
            Serial.print("[STEP] Amplitude="); Serial.print(StepAmplitude);
            Serial.print("V Duration="); Serial.print(StepTime / 1000.0);
            Serial.print("s Direction="); Serial.println(StepMotorDirection ? "FWD" : "REV");
        } else {
            experimentActive = false;
            flag_step = true;
            StepAmplitude = 0;
            StepTime = 0;
            MotorSpeed = 0;
            StepMotorDirection = 1;
            MotorDirection = StepMotorDirection;
            SetMotorControl();
            Serial.println("[STEP] ✗ Stopped");
        }
    }

    // Step Parameters - Only update when NOT in PID mode
    if (currentExperimentMode != PID_MODE && topic_str == "trenes/step/amplitude") {
        StepAmplitude = mensaje.toFloat();
        StepAmplitude = constrain(StepAmplitude, 0.0, v_batt);
        client.publish("trenes/step/amplitude/status", String(StepAmplitude, 1).c_str());
        Serial.print("[STEP] Amplitude updated: "); Serial.println(StepAmplitude);
    }
    if (currentExperimentMode != PID_MODE && topic_str == "trenes/step/time") {
        float time_seconds = mensaje.toFloat();
        StepTime = time_seconds * 1000;
        StepTime = constrain(StepTime, 0, 20000);
        client.publish("trenes/step/time/status", String(time_seconds, 1).c_str());
        Serial.print("[STEP] Duration updated: "); Serial.println(time_seconds);
    }
    if (currentExperimentMode != PID_MODE && topic_str == "trenes/step/direction") {
        StepMotorDirection = mensaje.toInt();
        StepMotorDirection = constrain(StepMotorDirection, 0, 1);
        client.publish("trenes/step/direction/status", String(StepMotorDirection).c_str());
        Serial.print("[STEP] Direction updated: "); Serial.println(StepMotorDirection ? "FWD" : "REV");
    }
    if (currentExperimentMode != PID_MODE && topic_str == "trenes/step/vbatt") {
        v_batt = mensaje.toFloat();
        v_batt = constrain(v_batt, 0.0, 8.4);
        client.publish("trenes/step/vbatt/status", String(v_batt, 1).c_str());
        Serial.print("[STEP] VBatt updated: "); Serial.println(v_batt);
    }
    if (currentExperimentMode != PID_MODE && topic_str == "trenes/step/request_params") {
        client.publish("trenes/step/amplitude/status", String(StepAmplitude, 1).c_str());
        client.publish("trenes/step/time/status", String(StepTime / 1000.0, 1).c_str());
        client.publish("trenes/step/direction/status", String(StepMotorDirection).c_str());
        client.publish("trenes/step/vbatt/status", String(v_batt, 1).c_str());
        Serial.println("[STEP] Parameters requested - sent status");
    }
}

// =============================================================================
// WiFi Setup
// =============================================================================
void setup_wifi() {
    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);
    
    WiFi.mode(WIFI_STA);
    esp_wifi_set_ps(WIFI_PS_NONE);
    WiFi.begin(ssid, password);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    
    // Start UDP
    udp.begin(localUDPPort);
    Serial.print("UDP listening on port ");
    Serial.println(localUDPPort);
}

// =============================================================================
// MQTT Reconnect - NON-BLOCKING VERSION
// =============================================================================
void attempt_mqtt_reconnect() {
    // Single reconnection attempt - does NOT block!
    if (client.connect(carro.c_str())) {
        Serial.println("✓ MQTT connected!");

        // Subscribe to PID topics
        client.subscribe("trenes/sync");
        client.subscribe("trenes/carroD/p");
        client.subscribe("trenes/carroD/i");
        client.subscribe("trenes/carroD/d");
        client.subscribe("trenes/ref");
        client.subscribe("trenes/carroD/request_params");

        // Subscribe to Step Response topics
        client.subscribe("trenes/step/sync");
        client.subscribe("trenes/step/amplitude");
        client.subscribe("trenes/step/time");
        client.subscribe("trenes/step/direction");
        client.subscribe("trenes/step/vbatt");
        client.subscribe("trenes/step/request_params");

        Serial.println("✓ Subscribed to all topics (PID + Step)");
        mqtt_retry_count = 0;
    } else {
        mqtt_retry_count++;
        Serial.print("✗ MQTT failed, rc=");
        Serial.print(client.state());
        Serial.print(" (will retry in ");
        Serial.print(MQTT_RECONNECT_INTERVAL / 1000);
        Serial.println("s)");

        // If too many failures, provide diagnostic info
        if (mqtt_retry_count % 5 == 0) {
            Serial.println("[DIAGNOSTIC] MQTT connection issues:");
            Serial.print("  - WiFi connected: "); Serial.println(WiFi.status() == WL_CONNECTED ? "YES" : "NO");
            Serial.print("  - WiFi RSSI: "); Serial.print(WiFi.RSSI()); Serial.println(" dBm");
            Serial.print("  - Broker IP: "); Serial.println(mqtt_server);
            Serial.print("  - Free heap: "); Serial.print(ESP.getFreeHeap()); Serial.println(" bytes");
        }
    }
}

// Initial MQTT connection with retry for setup phase
void initial_mqtt_connect() {
    int attempts = 0;
    const int MAX_ATTEMPTS = 10;

    Serial.print("Connecting to MQTT broker at ");
    Serial.print(mqtt_server);
    Serial.println("...");

    while (!client.connected() && attempts < MAX_ATTEMPTS) {
        Serial.print("  Attempt ");
        Serial.print(attempts + 1);
        Serial.print("/");
        Serial.print(MAX_ATTEMPTS);
        Serial.print("... ");

        attempt_mqtt_reconnect();

        if (!client.connected()) {
            delay(2000);  // Wait before next attempt (only during setup)
        }
        attempts++;
    }

    if (client.connected()) {
        Serial.println("✓ Initial MQTT connection successful!");
    } else {
        Serial.println("⚠ MQTT connection failed, will retry in background");
        Serial.println("  UDP data will still work, but parameter control disabled");
    }
}

// =============================================================================
// UDP Data Sending
// =============================================================================
void send_udp_pid_data() {
    uint32_t time_now = millis();
    double u = u_distancia;  // Get pure PID output
    String cadena = String(time_now) + "," + 
                    String(distancia) + "," + 
                    String(x_ref) + "," + 
                    String(error_distancia) + "," + 
                    String(Kp) + "," + 
                    String(Ki) + "," + 
                    String(Kd) + "," + 
                    String(u);  // Send PID output, NOT MotorSpeed
    
    cadena.toCharArray(msg, cadena.length() + 1);
    udp.beginPacket(mqtt_server, udpPort);
    udp.print(msg);
    udp.endPacket();
}

void send_udp_step_data() {
    uint32_t time_now = millis();
    String cadena = String(delta) + "," + 
                    String(time_now) + "," + 
                    String(StepMotorDirection) + "," +  // FIXED: Use Step-specific direction
                    String(v_batt) + "," + 
                    String(medi) + "," + 
                    String(StepAmplitude) + "," + 
                    String(MotorSpeed);
    
    cadena.toCharArray(msg, cadena.length() + 1);
    udp.beginPacket(mqtt_server, udpPort);
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
    
    // Moving average filter
    newSum = movingSum(arrNumbers, &sum, pos, len, medi);
    newAvg = newSum / (float)len;
    pos++;
    if (pos >= len) {
        pos = 0;
    }
    oldAvg = newAvg;
    medi = (0.8 * newAvg + 0.2 * oldAvg) / 10;  // Convert to cm
}

int movingSum(int *ptrArrNumbers, long *ptrSum, int pos, int len, int nextNum) {
    *ptrSum = *ptrSum - ptrArrNumbers[pos] + nextNum;
    ptrArrNumbers[pos] = nextNum;
    return *ptrSum;
}

