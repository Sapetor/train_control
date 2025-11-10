/*
 * COMPLETE VERSION - Unified Train Control Firmware
 * Supports PID Control + Step Response + Deadband Calibration
 *
 * CRITICAL FIXES APPLIED:
 * 1. Only call SetTunings when MQTT updates parameters (not every loop)
 * 2. Proper PID configuration order (SetSampleTime before Compute)
 * 3. Fixed control logic to prevent motor direction flipping
 * 4. Improved mode switching to preserve integrator state
 * 5. RESTORED original deadband default (300, empirically determined)
 * 6. REMOVED artificial safety cap on auto-detected deadband
 *
 * NEW FEATURE:
 * - Deadband Calibration Mode: Observable experiment via dashboard
 * - Real-time PWM vs Distance visualization
 * - CSV data logging
 * - MQTT-triggered on demand
 *
 * Experiment Modes:
 * - PID_MODE: Closed-loop PID control with distance tracking
 * - STEP_MODE: Open-loop step response for system identification
 * - DEADBAND_MODE: Deadband calibration with real-time monitoring
 *
 * MQTT Topics:
 * - trenes/sync -> Starts PID experiment
 * - trenes/step/sync -> Starts Step Response experiment
 * - trenes/deadband/sync -> Starts Deadband Calibration experiment
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
#define DEADBAND_MODE 2

int currentExperimentMode = PID_MODE;
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

// Separate direction variables for each mode
int PIDMotorDirection = 1;
int StepMotorDirection = 1;
int DeadbandMotorDirection = 1;  // NEW: For deadband calibration
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
int deadband = 300;  // RESTORED: Original empirically-determined value
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
// NEW: Delay step application to get baseline samples
int stepSampleCounter = 0;
const int STEP_DELAY_SAMPLES = 2;  // Number of samples to wait before applying step
double appliedStepValue = 0.0;     // Actual step value being applied (0 initially, then StepAmplitude)

// =============================================================================
// Deadband Calibration Mode Variables (NEW)
// =============================================================================
bool flag_deadband = true;
uint32_t tiempo_inicial_deadband = 0;
int calibrated_deadband = 0;
double initial_distance = 0;
int pwm_increment = 1;  // PWM increment per step
int pwm_delay = 40;     // Delay between increments (ms)
double motion_threshold = 0.08;  // Motion detection threshold (cm) - was 0.8mm
int max_pwm_test = 800;  // Safety limit
bool motion_detected = false;
int Frequency = 100;  // PWM frequency for calibration

// =============================================================================
// Configuration Flags
// =============================================================================
bool AUTO_CALIBRATE_ON_BOOT = false;  // Set true to run calibration on boot

// =============================================================================
// Setup
// =============================================================================
void setup() {
    Serial.begin(115200);
    Serial.println("==============================================");
    Serial.println("  Unified Train Control - COMPLETE VERSION");
    Serial.println("  Modes: PID + Step Response + Deadband Cal");
    Serial.println("  Deadband: Observable Experiment");
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

    // PID Configuration - Proper Order
    myPID.SetSampleTime(SampleTime);
    myPID.SetOutputLimits(umin, umax);
    myPID.SetTunings(Kp, Ki, Kd);
    myPID.SetMode(MANUAL);

    Serial.println("PID Configuration:");
    Serial.print("  Sample Time: "); Serial.print(SampleTime); Serial.println("ms");
    Serial.print("  Output Limits: ±"); Serial.println(umax);
    Serial.print("  Deadband Default: "); Serial.println(deadband);

    // Optional: Auto-calibrate on boot
    if (AUTO_CALIBRATE_ON_BOOT) {
        Serial.println("Running deadband calibration on boot...");
        run_deadband_calibration();
        deadband = calibrated_deadband;
        Serial.print("Deadband set to: "); Serial.println(deadband);
    }

    Serial.println("==============================================");
    Serial.println("Setup Complete! Waiting for experiment start...");
    Serial.println("Available experiments:");
    Serial.println("  - PID Control: trenes/sync");
    Serial.println("  - Step Response: trenes/step/sync");
    Serial.println("  - Deadband Calibration: trenes/deadband/sync");
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
        int deadband_comp = deadband;  // Use configured deadband
        MotorSpeed = constrain(int(u + deadband_comp), 0, 1024);
    }
    else if (u < -lim) {
        PIDMotorDirection = 0;
        int deadband_comp = deadband;  // Use configured deadband
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

        // Reset step delay counter and applied value
        stepSampleCounter = 0;
        appliedStepValue = 0.0;
        Serial.print("  Waiting for "); Serial.print(STEP_DELAY_SAMPLES); Serial.println(" baseline samples before applying step...");
    }

    read_ToF_sensor();

    // Apply step only after collecting baseline samples
    if (stepSampleCounter < STEP_DELAY_SAMPLES) {
        // Baseline period - motor off, step = 0
        appliedStepValue = 0.0;
        MotorSpeed = 0;
        stepSampleCounter++;
        if (stepSampleCounter == STEP_DELAY_SAMPLES) {
            Serial.println("[STEP] Baseline samples collected, applying step now!");
        }
    } else {
        // Apply the step
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
        // Don't reset parameters when experiment completes - keep them for next experiment
        // StepTime = 0;
        // StepAmplitude = 0;
        experimentActive = false;
        MotorSpeed = 0;
        SetMotorControl();
    }

    delay(21);
}

// =============================================================================
// Deadband Calibration Experiment Loop (NEW)
// =============================================================================
void loop_deadband_experiment() {
    if (flag_deadband == false) {
        flag_deadband = true;
        tiempo_inicial_deadband = millis();
        Serial.println("[DEADBAND] Calibration started!");
        Serial.print("  Direction: "); Serial.println(DeadbandMotorDirection ? "Forward" : "Reverse");
        Serial.print("  Motion threshold: "); Serial.print(motion_threshold); Serial.println(" cm");

        // Record initial position - take average of 10 readings to reduce noise
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

        // Set PWM frequency
        ledcAttach(Control_v, Frequency, 10);

        Serial.print("  Initial distance (averaged): "); Serial.print(initial_distance); Serial.println(" cm");
        Serial.println("  Increasing PWM from 0 until motion detected...");
        Serial.println("  (Ignoring sensor noise - PWM will increment regardless)");
    }

    // Always increment PWM (ignore sensor noise during ramp-up)
    MotorSpeed += pwm_increment;
    MotorDirection = DeadbandMotorDirection;
    SetMotorControl();

    // Read current distance - take average of 3 readings
    double sum = 0;
    for (int i = 0; i < 3; i++) {
        read_ToF_sensor();
        sum += medi;
        delay(5);
    }
    double current_distance = sum / 3.0;
    double distance_change = abs(current_distance - initial_distance);

    // Send UDP data for dashboard visualization
    send_udp_deadband_data();

    // Check for motion - only trust readings after PWM has started (PWM > 50)
    if (distance_change >= motion_threshold && MotorSpeed > 50) {
        // Motion detected!
        motion_detected = true;
        calibrated_deadband = MotorSpeed;

        Serial.println("========================================");
        Serial.println("✓ MOTION DETECTED!");
        Serial.print("  Deadband PWM: "); Serial.println(calibrated_deadband);
        Serial.print("  Initial distance: "); Serial.print(initial_distance); Serial.println(" cm");
        Serial.print("  Final distance: "); Serial.print(current_distance); Serial.println(" cm");
        Serial.print("  Distance moved: "); Serial.print(distance_change); Serial.println(" cm");
        Serial.println("========================================");

        // IMPORTANT: Send final UDP packet with motion_detected=1 before stopping
        send_udp_deadband_data();
        delay(50);  // Give time for UDP packet to be sent

        // Stop motor
        MotorSpeed = 0;
        SetMotorControl();

        // Publish result to MQTT
        client.publish("trenes/deadband/result", String(calibrated_deadband).c_str());

        // End experiment
        delay(1000);
        experimentActive = false;
        flag_deadband = true;

        return;
    }

    // Report progress every 50 PWM units
    if (MotorSpeed % 50 == 0) {
        Serial.print("  PWM: "); Serial.print(MotorSpeed);
        Serial.print(" - Distance: "); Serial.print(current_distance);
        Serial.print(" cm (change: "); Serial.print(distance_change);
        Serial.println(" cm)");
    }

    delay(pwm_delay);

    // Safety timeout
    if (MotorSpeed >= max_pwm_test) {
        Serial.println("========================================");
        Serial.println("⚠ WARNING: Reached maximum PWM without motion!");
        Serial.println("  Check if train is stuck or sensor calibration");
        Serial.print("  Using default deadband: "); Serial.println(deadband);
        Serial.println("========================================");

        calibrated_deadband = deadband;  // Use default
        MotorSpeed = 0;
        SetMotorControl();

        client.publish("trenes/deadband/result", String(calibrated_deadband).c_str());
        client.publish("trenes/deadband/error", "Timeout - no motion detected");

        experimentActive = false;
        flag_deadband = true;
    }
}

// =============================================================================
// Helper: Run Deadband Calibration (for boot-time auto-cal)
// =============================================================================
void run_deadband_calibration() {
    // This is the original deadBand() function logic
    // Called at boot if AUTO_CALIBRATE_ON_BOOT is true

    read_ToF_sensor();
    double initial = medi;

    MotorSpeed = 0;
    MotorDirection = 1;  // Forward
    ledcAttach(Control_v, 100, 10);

    Serial.println("Auto-calibrating deadband...");

    while (true) {
        read_ToF_sensor();
        double current = medi;

        if (abs(initial - current) < 0.1) {  // No motion yet
            MotorSpeed += 1;
            SetMotorControl();
            delay(40);

            read_ToF_sensor();
            current = medi;

            if (abs(initial - current) >= 0.08) {  // Motion detected
                calibrated_deadband = MotorSpeed;
                MotorSpeed = 0;
                SetMotorControl();
                Serial.print("Deadband found: "); Serial.println(calibrated_deadband);
                return;
            }
        }

        if (MotorSpeed > 800) {
            Serial.println("Timeout - using default 300");
            calibrated_deadband = 300;
            MotorSpeed = 0;
            SetMotorControl();
            return;
        }
    }
}

// =============================================================================
// MQTT Callback
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
        if (topic_str == "trenes/carroD/p") {
            double new_Kp = mensaje.toFloat();
            if (new_Kp != Kp) {
                Kp = new_Kp;
                // Apply parameters IMMEDIATELY if in PID mode
                if (currentExperimentMode == PID_MODE && experimentActive) {
                    myPID.SetTunings(Kp, Ki, Kd);
                    Serial.print("[PID] Kp updated immediately: ");
                    Serial.println(Kp);
                }
                pid_params_changed = true;
                client.publish("trenes/carroD/p/status", String(Kp).c_str());
            }
        }
        else if (topic_str == "trenes/carroD/i") {
            double new_Ki = mensaje.toFloat();
            if (new_Ki != Ki) {
                Ki = new_Ki;
                // Apply parameters IMMEDIATELY if in PID mode
                if (currentExperimentMode == PID_MODE && experimentActive) {
                    myPID.SetTunings(Kp, Ki, Kd);
                    Serial.print("[PID] Ki updated immediately: ");
                    Serial.println(Ki);
                }
                pid_params_changed = true;
                client.publish("trenes/carroD/i/status", String(Ki).c_str());
            }
        }
        else if (topic_str == "trenes/carroD/d") {
            double new_Kd = mensaje.toFloat();
            if (new_Kd != Kd) {
                Kd = new_Kd;
                // Apply parameters IMMEDIATELY if in PID mode
                if (currentExperimentMode == PID_MODE && experimentActive) {
                    myPID.SetTunings(Kp, Ki, Kd);
                    Serial.print("[PID] Kd updated immediately: ");
                    Serial.println(Kd);
                }
                pid_params_changed = true;
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
            // Don't reset parameters when stopping - keep them for next start
            // StepAmplitude = 0;
            // StepTime = 0;
            MotorSpeed = 0;
            StepMotorDirection = 1;
            MotorDirection = StepMotorDirection;
            SetMotorControl();
            Serial.println("[STEP] Stopped");
        }
    }
    // IMPORTANT: Allow setting step parameters regardless of current mode
    // This allows dashboard to set parameters before switching to STEP_MODE
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

    // =========================================================================
    // Deadband Calibration Topics (NEW)
    // =========================================================================
    if (topic_str == "trenes/deadband/sync") {
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
    else if (topic_str == "trenes/deadband/direction") {
        DeadbandMotorDirection = mensaje.toInt();
        DeadbandMotorDirection = constrain(DeadbandMotorDirection, 0, 1);
        client.publish("trenes/deadband/direction/status", String(DeadbandMotorDirection).c_str());
    }
    else if (topic_str == "trenes/deadband/threshold") {
        motion_threshold = mensaje.toFloat();
        motion_threshold = constrain(motion_threshold, 0.01, 1.0);  // 0.01-1.0 cm
        client.publish("trenes/deadband/threshold/status", String(motion_threshold, 2).c_str());
    }
    else if (topic_str == "trenes/deadband/request_params") {
        client.publish("trenes/deadband/direction/status", String(DeadbandMotorDirection).c_str());
        client.publish("trenes/deadband/threshold/status", String(motion_threshold, 2).c_str());
        client.publish("trenes/deadband/result", String(calibrated_deadband).c_str());
    }
    else if (topic_str == "trenes/deadband/apply") {
        // Apply calibrated deadband to PID mode
        if (mensaje == "True" && calibrated_deadband > 0) {
            deadband = calibrated_deadband;
            client.publish("trenes/deadband/applied", String(deadband).c_str());
            Serial.print("[DEADBAND] Applied to PID mode: "); Serial.println(deadband);
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

            // Subscribe to Deadband Calibration topics (NEW)
            client.subscribe("trenes/deadband/sync");
            client.subscribe("trenes/deadband/direction");
            client.subscribe("trenes/deadband/threshold");
            client.subscribe("trenes/deadband/request_params");
            client.subscribe("trenes/deadband/apply");

            Serial.println("Subscribed to all topics (PID + Step + Deadband)");
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
    udp.beginPacket(mqtt_server, udpPort);
    udp.print(msg);
    udp.endPacket();
}

void send_udp_step_data() {
    uint32_t time_now = millis();
    // NEW: Added appliedStepValue to show when step is actually applied (0 for baseline samples)
    String cadena = String(delta) + "," +
                    String(time_now) + "," +
                    String(StepMotorDirection) + "," +
                    String(v_batt) + "," +
                    String(medi) + "," +
                    String(StepAmplitude) + "," +
                    String(MotorSpeed) + "," +
                    String(appliedStepValue);  // NEW: Shows 0.0 during baseline, then StepAmplitude

    cadena.toCharArray(msg, cadena.length() + 1);
    udp.beginPacket(mqtt_server, udpPort);
    udp.print(msg);
    udp.endPacket();
}

void send_udp_deadband_data() {
    // NEW: Send deadband calibration data
    // Format: time, pwm, distance, initial_distance, motion_detected
    uint32_t time_now = millis() - tiempo_inicial_deadband;
    String cadena = String(time_now) + "," +
                    String(MotorSpeed) + "," +
                    String(medi) + "," +
                    String(initial_distance) + "," +
                    String(motion_detected ? 1 : 0);

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

    newSum = movingSum(arrNumbers, &sum, pos, len, medi);
    newAvg = newSum / (float)len;
    pos++;
    if (pos >= len) {
        pos = 0;
    }
    oldAvg = newAvg;
    medi = (0.8 * newAvg + 0.2 * oldAvg) / 10.0;  // Convert to cm
}

int movingSum(int *ptrArrNumbers, long *ptrSum, int pos, int len, int nextNum) {
    *ptrSum = *ptrSum - ptrArrNumbers[pos] + nextNum;
    ptrArrNumbers[pos] = nextNum;
    return *ptrSum;
}
