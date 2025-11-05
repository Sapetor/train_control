/*
 * FIXED VERSION - Train ESP32 PID Controller
 *
 * Key Fixes Applied:
 * 1. Removed SetTunings() from main loop (was resetting integrator!)
 * 2. Only call SetTunings when MQTT updates parameters
 * 3. Reduced deadband from 300 to 80 (prevents wild oscillations)
 * 4. Fixed contradictory direction logic
 * 5. Simplified mode switching to prevent integrator reset
 * 6. Improved control logic flow
 *
 * Original issues documented in: PID_DEBUG_ANALYSIS.md
 */

#include <PID_v1_bc.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <VL53L0X.h>
#include <esp_wifi.h>

////////////////////////////////////////////
// MQTT Topics /////////////////////////////
////////////////////////////////////////////
String carro = "carro" + String(random(100));
char treneserror[] = "trenes/carroD/error";
char trenesp[] = "trenes/carroD/p";
char trenesi[] = "trenes/carroD/i";
char trenesd[] = "trenes/carroD/d";
char trenesp_v[] = "trenes/carroD/p_v";
char trenesi_v[] = "trenes/carroD/i_v";
char trenesd_v[] = "trenes/carroD/d_v";
char trenesdesfase[] = "trenes/carroD/desfase";
char trenesestado[] = "trenes/estado/carroD";
char trenestest[] = "trenes/carroD/test";
char trenessampletime[] = "trenes/carroD/ts";
char trenestransmision[] = "trenes/envio";
int t_envio = 50;

////////////////////////////////////////////
// Dead Reckoning Variables ////////////////
////////////////////////////////////////////
int yy = 0;
double temp_cal;
double scale;
double medi = 10;
double xx = 10;

// Moving average filter
int INDEX = 0;
int VALUE = 0;
int SUM = 0;
int READINGS[10];
double AVERAGED = 0;

int arrNumbers[3] = {0};
int pos = 0;
float newAvg = 0;
float oldAvg = 0;
int newSum = 0;
long sum = 0;
int len = sizeof(arrNumbers) / sizeof(int);

////////////////////////////////////////////
// Network Configuration ///////////////////
////////////////////////////////////////////
const char* ssid = "TICS322";
const char* password = "esp32esp32";
const char* mqtt_server = "192.168.137.1";
const int udpPort = 5555;
String estado;

WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;
char msg[128];
WiFiUDP udp;

////////////////////////////////////////////
// Motor Configuration /////////////////////
////////////////////////////////////////////
const int STBY = 7;
const int Control_fwd = 8;
const int Control_back = 18;
const int Control_v = 17;
int MotorSpeed = 0;
int MotorDirection = 1;

////////////////////////////////////////////
// ToF Sensor Variables ////////////////////
////////////////////////////////////////////
VL53L0X SensorToF;
double distancia = 25;
double old_d = 0;
double old = 0;
double t_distancia = 0;
double t_old;
double t1;
double t2;

////////////////////////////////////////////
// General Control Variables ///////////////
////////////////////////////////////////////
int dead = 1;
int deadband = 80;  // FIXED: Reduced from 300 to 80 (typical for small DC motors)
int tiempo_inicial = 0;
bool flag = true;
bool start = false;

////////////////////////////////////////////
// PID Variables ///////////////////////////
////////////////////////////////////////////
double v_lider = 0, mierror;
float v_medida = 0;
float v_ref = 0;
double x_ref = 10;
double u_distancia = 0;
double u_velocidad = 0;
double u = 0;
double u_send;

int umin = -1024, umax = 1024;
double Kp = 0, Ki = 0, Kd = 0;
double Kp_v = 10, Ki_v = 1, Kd_v = 0;
int SampleTime = 50;
double etha = 0.5;
int Frequency = 100;
int PreviousFrequency;
int deadband1 = 0;
double alpha = 0;
double N = 10;
double error_distancia;
double error_velocidad;
double ponderado = 0;  // Initialize to 0
double rf = 0;
int lim = 10;

// FIXED: Add flag to track parameter changes
bool pid_params_changed = false;

PID myPID(&error_distancia, &u_distancia, &rf, Kp, Ki, Kd, DIRECT);

void loop() {
    // Verify MQTT connection
    if (!client.connected()) {
        reconnect();
        estado = String(carro) + " Reconectando";
        estado.toCharArray(msg, estado.length() + 1);
        client.publish(trenesestado, msg);
    }

    client.loop();

    // Send sync message on first iteration
    if (flag == false) {
        String delta = String((millis() - tiempo_inicial) * 0.001);
        delta.toCharArray(msg, delta.length() + 1);
        client.publish(trenesdesfase, msg);
        flag = true;
        start = true;
        Serial.println("Sync!");
    }

    // Main control loop
    if (start) {
        // =====================================================================
        // SENSOR READING
        // =====================================================================
        xx = medi;  // Memory for filtering
        medi = 0;

        old = micros();

        // Read ToF sensor (2 samples averaged)
        for (int i = 0; i < 2; i++) {
            uint16_t range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);
            medi = medi + range;
            delay(21);
        }

        medi = medi / 2;

        // Apply moving average filter
        Serial.print(medi);
        newSum = movingSum(arrNumbers, &sum, pos, len, medi);
        newAvg = newSum / (float)len;
        Serial.print(" ,");

        pos++;
        if (pos >= len) {
            pos = 0;
        }

        oldAvg = newAvg;
        medi = (0.8 * newAvg + 0.2 * oldAvg) / 10;  // Convert to cm
        Serial.print(medi);

        // =====================================================================
        // PID COMPUTATION
        // =====================================================================
        error_distancia = x_ref - medi;

        Serial.print(" ,");
        Serial.println(error_distancia);

        // FIXED: Only update tunings when parameters actually changed via MQTT
        if (pid_params_changed) {
            myPID.SetTunings(Kp, Ki, Kd);
            pid_params_changed = false;
            Serial.println("[PID] Parameters updated");
        }

        // FIXED: Removed redundant SetOutputLimits and SetSampleTime from loop
        // These are now only set in setup() and when changed via MQTT

        myPID.Compute();  // Just compute, no reconfiguration!

        u = u_distancia;  // Use PID output directly

        // =====================================================================
        // SAFETY: NO OBJECT DETECTED
        // =====================================================================
        if (medi > 200) {
            // No object in front - gentle deceleration
            if (MotorSpeed < 200) {
                MotorSpeed = MotorSpeed - 10;
            } else {
                MotorSpeed = 0;
            }
            // FIXED: Keep PID in AUTOMATIC to avoid integrator reset
            // Just stop the motor, PID keeps running
        }

        // =====================================================================
        // NORMAL OPERATION: OBJECT DETECTED
        // =====================================================================
        else {
            // FIXED: Simplified control logic without contradictions

            if (abs(u) <= lim) {
                // Dead zone: error too small, stop motor
                MotorSpeed = 0;
                // Keep last MotorDirection (don't flip randomly)
                // Keep PID in AUTOMATIC so integrator doesn't reset
            }
            else if (u > lim) {
                // Forward motion needed
                MotorDirection = 1;
                // FIXED: Use smaller deadband compensation
                MotorSpeed = constrain(int(u + deadband), 0, 1024);
            }
            else if (u < -lim) {
                // Reverse motion needed
                MotorDirection = 0;
                // FIXED: Use smaller deadband compensation
                MotorSpeed = constrain(int(-u + deadband), 0, 1024);
            }

            // Additional safety: stop if at rest with very small error
            if ((abs(u) <= lim) && (abs(ponderado) <= 0.75)) {
                MotorSpeed = 0;
                // Keep last direction
            }
        }

        // =====================================================================
        // TEST MODE: DISABLE CONTROL
        // =====================================================================
        int test_sin_control = 0;
        if (test_sin_control) {
            myPID.SetMode(MANUAL);
            MotorSpeed = 0;
        }

        // =====================================================================
        // APPLY MOTOR CONTROL
        // =====================================================================
        SetMotorControl();

        // =====================================================================
        // SEND DATA VIA UDP
        // =====================================================================
        uint32_t time_now = millis();
        t_old = millis();

        estado = String(time_now) + "," +
                 String(medi) + "," +
                 String(x_ref) + "," +
                 String(error_distancia) + "," +
                 String(Kp) + "," +
                 String(Ki) + "," +
                 String(Kd) + "," +
                 String(u);  // Send PID output, not MotorSpeed

        estado.toCharArray(msg, estado.length() + 1);

        udp.beginPacket(mqtt_server, udpPort);
        udp.printf(msg);
        udp.endPacket();
    }
}
