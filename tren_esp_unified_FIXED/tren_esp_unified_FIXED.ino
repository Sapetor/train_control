/*
 * FIXED VERSION - Unified Train Control Firmware
 * Supports both PID Control and Step Response experiments
 *
 * CRITICAL FIXES APPLIED:
 * 1. Removed redundant PID configuration from loop (was resetting integrator!)
 * 2. Only call SetTunings when MQTT updates parameters
 * 3. Fixed control logic to prevent motor direction flipping
 * 4. Improved mode switching to preserve integrator state
 * 5. Better deadband compensation (capped at reasonable values)
 *
 * Experiment Modes:
 * - PID_MODE: Closed-loop PID control with distance tracking
 * - STEP_MODE: Open-loop step response for system identification
 *
 * MQTT Topics automatically switch experiment mode:
 * - trenes/sync -> Starts PID experiment
 * - trenes/step/sync -> Starts Step Response experiment
 *
 * Original issues documented in: PID_DEBUG_ANALYSIS.md
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

// Separate direction variables for each mode to prevent interference
int PIDMotorDirection = 1;   // Direction for PID mode (1=Forward, 0=Reverse)
int StepMotorDirection = 1;  // Direction for Step mode (1=Forward, 0=Reverse)
int MotorDirection = 1;      // Global direction (set from mode-specific variables)

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
double error_distancia = 0;
double u_distancia = 0;
double rf = 0;
double Kp = 0, Ki = 0, Kd = 0;
int SampleTime = 50;
int umin = -1024, umax = 1024;
int t_envio = 50;
double etha = 0.5;
int deadband = 80;  // FIXED: Reduced from 300 to 80
int lim = 10;  // Minimum PID output threshold
double ponderado = 0;  // Weighted error for velocity-based control
bool flag_pid = true;
uint32_t tiempo_inicial_pid = 0;

// FIXED: Add flag to track parameter changes
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

// =============================================================================
// Setup
// =============================================================================
void setup() {
    Serial.begin(115200);
    Serial.println("==============================================");
    Serial.println("  Unified Train Control - FIXED VERSION");
    Serial.println("  Supports: PID Control + Step Response");
    Serial.println("  PID Issues Corrected");
    Serial.println("==============================================");

    // WiFi Setup
    setup_wifi();

    // MQTT Setup
    client.setServer(mqtt_server, 1883);
    client.setCallback(mqtt_callback);
    reconnect_mqtt();

    // Motor Setup
    setup_motor();

    // ToF Sensor Setup
    setup_ToF();

    // FIXED: PID Configuration - Proper Order!
    // 1. Sample time FIRST
    myPID.SetSampleTime(SampleTime);

    // 2. Output limits
    myPID.SetOutputLimits(umin, umax);

    // 3. Initial tunings
    myPID.SetTunings(Kp, Ki, Kd);

    // 4. Start in MANUAL mode (will enable on sync)
    myPID.SetMode(MANUAL);

    Serial.println("PID Configuration:");
    Serial.print("  Sample Time: "); Serial.print(SampleTime); Serial.println("ms");
    Serial.print("  Output Limits: ±"); Serial.println(umax);
    Serial.print("  Initial Gains - Kp:"); Serial.print(Kp);
    Serial.print(", Ki:"); Serial.print(Ki);
    Serial.print(", Kd:"); Serial.println(Kd);
    Serial.print("  Deadband: "); Serial.println(deadband);

    Serial.println("==============================================");
    Serial.println("Setup Complete! Waiting for experiment start...");
    Serial.println("==============================================");
}

// =============================================================================
// Main Loop
// =============================================================================
void loop() {
    // Maintain MQTT connection
    if (!client.connected()) {
        reconnect_mqtt();
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
// PID Experiment Loop - FIXED VERSION
// =============================================================================
void loop_pid_experiment() {
    // Sync message on first iteration
    if (flag_pid == false) {
        flag_pid = true;
        tiempo_inicial_pid = millis();
        Serial.println("[PID] Experiment started!");

        // FIXED: Only enable PID, don't reconfigure
        // Configuration was done in setup() already
        myPID.SetMode(AUTOMATIC);

        // Reset direction to default
        PIDMotorDirection = 1;
    }

    // FIXED: Update tunings ONLY when parameters changed via MQTT
    if (pid_params_changed) {
        myPID.SetTunings(Kp, Ki, Kd);
        pid_params_changed = false;
        Serial.print("[PID] Parameters updated - Kp:");
        Serial.print(Kp); Serial.print(", Ki:");
        Serial.print(Ki); Serial.print(", Kd:");
        Serial.println(Kd);
    }

    // Read sensor
    read_ToF_sensor();
    distancia = medi;

    // Calculate error
    error_distancia = x_ref - distancia;

    // FIXED: Just compute PID, no reconfiguration!
    myPID.Compute();

    double u = u_distancia;  // PID output

    // =========================================================================
    // SAFETY: No object in front (distance > 200cm)
    // =========================================================================
    if (distancia > 200) {
        // Gentle deceleration
        if (MotorSpeed < 200) {
            MotorSpeed = MotorSpeed - 10;
        } else {
            MotorSpeed = 0;
        }
        // FIXED: Keep PID in AUTOMATIC to avoid integrator reset
        // Just stop motor, PID keeps running in background
        SetMotorControl();
        send_udp_pid_data();
        delay(SampleTime);
        return;
    }

    // =========================================================================
    // NORMAL OPERATION: Object detected
    // =========================================================================
    // FIXED: Simplified control logic without contradictions

    if (abs(u) <= lim) {
        // Dead zone: error too small
        MotorSpeed = 0;
        // Keep last PIDMotorDirection (don't flip randomly)
        // Keep PID in AUTOMATIC to preserve integrator
    }
    else if (u > lim) {
        // Forward motion needed
        PIDMotorDirection = 1;
        // Apply deadband compensation (capped at reasonable value)
        int deadband_comp = min(deadband, 100);  // Cap at 100
        MotorSpeed = constrain(int(u + deadband_comp), 0, 1024);
    }
    else if (u < -lim) {
        // Reverse motion needed
        PIDMotorDirection = 0;
        // Apply deadband compensation (capped at reasonable value)
        int deadband_comp = min(deadband, 100);  // Cap at 100
        MotorSpeed = constrain(int(-u + deadband_comp), 0, 1024);
    }

    // Additional stop condition when at rest
    if ((abs(u) <= lim) && (abs(ponderado) <= 0.75)) {
        MotorSpeed = 0;
        // Keep last direction
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
        Serial.print("  Direction: "); Serial.println(StepMotorDirection ? "Forward" : "Reverse");

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
// MQTT Callback - FIXED VERSION
// =============================================================================
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
    String mensaje = "";
    for (unsigned int i = 0; i < length; i++) {
        mensaje += (char)payload[i];
    }

    String topic_str = String(topic);
    Serial.print("[MQTT] "); Serial.print(topic_str); Serial.print(" = "); Serial.println(mensaje);

    // =========================================================================
    // PID Control Topics
    // =========================================================================
    if (topic_str == "trenes/sync") {
        if (mensaje == "True") {
            currentExperimentMode = PID_MODE;
            experimentActive = true;
            flag_pid = false;
            tiempo_inicial_pid = millis();
            PIDMotorDirection = 1;  // Reset to default direction
            Serial.println("[MODE] Switched to PID Control");
        } else {
            experimentActive = false;
            flag_pid = true;
            myPID.SetMode(MANUAL);
            u_distancia = 0;
            error_distancia = 0;
            MotorSpeed = 0;
            PIDMotorDirection = 1;  // Reset direction
            MotorDirection = PIDMotorDirection;
            SetMotorControl();
            Serial.println("[PID] Stopped");
        }
    }
    // FIXED: Only accept PID parameters when in PID mode or idle
    else if (currentExperimentMode != STEP_MODE) {
        if (topic_str == "trenes/carroD/p") {
            double new_Kp = mensaje.toFloat();
            if (new_Kp != Kp) {
                Kp = new_Kp;
                pid_params_changed = true;  // Signal loop to update
                client.publish("trenes/carroD/p/status", String(Kp).c_str());
            }
        }
        else if (topic_str == "trenes/carroD/i") {
            double new_Ki = mensaje.toFloat();
            if (new_Ki != Ki) {
                Ki = new_Ki;
                pid_params_changed = true;  // Signal loop to update
                client.publish("trenes/carroD/i/status", String(Ki).c_str());
            }
        }
        else if (topic_str == "trenes/carroD/d") {
            double new_Kd = mensaje.toFloat();
            if (new_Kd != Kd) {
                Kd = new_Kd;
                pid_params_changed = true;  // Signal loop to update
                client.publish("trenes/carroD/d/status", String(Kd).c_str());
            }
        }
        else if (topic_str == "trenes/ref") {
            double new_ref = mensaje.toFloat();
            if (new_ref != x_ref) {
                x_ref = new_ref;
                client.publish("trenes/carroD/ref/status", String(x_ref).c_str());
            }
        }
        else if (topic_str == "trenes/carroD/request_params") {
            client.publish("trenes/carroD/p/status", String(Kp).c_str());
            client.publish("trenes/carroD/i/status", String(Ki).c_str());
            client.publish("trenes/carroD/d/status", String(Kd).c_str());
            client.publish("trenes/carroD/ref/status", String(x_ref).c_str());
        }
    }

    // =========================================================================
    // Step Response Topics
    // =========================================================================
    if (topic_str == "trenes/step/sync") {
        if (mensaje == "True" && StepTime > 0 && StepAmplitude > 0) {
            currentExperimentMode = STEP_MODE;
            experimentActive = true;
            flag_step = false;
            tiempo_inicial_step = millis();
            Serial.println("[MODE] Switched to Step Response");
        } else {
            experimentActive = false;
            flag_step = true;
            StepAmplitude = 0;
            StepTime = 0;
            MotorSpeed = 0;
            StepMotorDirection = 1;  // Reset direction
            MotorDirection = StepMotorDirection;
            SetMotorControl();
            Serial.println("[STEP] Stopped");
        }
    }
    // Only accept Step parameters when in Step mode or idle
    else if (currentExperimentMode != PID_MODE || !experimentActive) {
        if (topic_str == "trenes/step/amplitude") {
            StepAmplitude = mensaje.toFloat();
            StepAmplitude = constrain(StepAmplitude, 0.0, v_batt);
            client.publish("trenes/step/amplitude/status", String(StepAmplitude, 1).c_str());
        }
        else if (topic_str == "trenes/step/time") {
            float time_seconds = mensaje.toFloat();
            StepTime = time_seconds * 1000;
            StepTime = constrain(StepTime, 0, 20000);
            client.publish("trenes/step/time/status", String(time_seconds, 1).c_str());
        }
        else if (topic_str == "trenes/step/direction") {
            StepMotorDirection = mensaje.toInt();
            StepMotorDirection = constrain(StepMotorDirection, 0, 1);
            client.publish("trenes/step/direction/status", String(StepMotorDirection).c_str());
        }
        else if (topic_str == "trenes/step/vbatt") {
            v_batt = mensaje.toFloat();
            v_batt = constrain(v_batt, 0.0, 8.4);
            client.publish("trenes/step/vbatt/status", String(v_batt, 1).c_str());
        }
        else if (topic_str == "trenes/step/request_params") {
            client.publish("trenes/step/amplitude/status", String(StepAmplitude, 1).c_str());
            client.publish("trenes/step/time/status", String(StepTime / 1000.0, 1).c_str());
            client.publish("trenes/step/direction/status", String(StepMotorDirection).c_str());
            client.publish("trenes/step/vbatt/status", String(v_batt, 1).c_str());
        }
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
// MQTT Reconnect
// =============================================================================
void reconnect_mqtt() {
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");

        if (client.connect(carro.c_str())) {
            Serial.println(" connected!");

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

            Serial.println("Subscribed to all topics (PID + Step)");
        } else {
            Serial.print(" failed, rc=");
            Serial.print(client.state());
            Serial.println(" - retrying in 5 seconds");
            delay(5000);
        }
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
                    String(StepMotorDirection) + "," +
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
