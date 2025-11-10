/*
 * FIXED VERSION - ESP32 Setup Module
 *
 * Key Fixes:
 * 1. Proper PID initialization order
 * 2. SetSampleTime BEFORE enabling PID
 * 3. Cleaner MQTT connection handling
 */

void setup() {
    //WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG,0);//disable brownout detector
    Serial.begin(115200);
    Serial.println("==============================================");
    Serial.println("  Train Control ESP32 - FIXED VERSION");
    Serial.println("  PID Issues Corrected - See PID_DEBUG_ANALYSIS.md");
    Serial.println("==============================================");

    /////////////////////////////////////
    ///       Network Setup        //////
    /////////////////////////////////////
    setup_wifi();
    setup_mqtt();

    /////////////////////////////////////
    ///       Motor Setup          //////
    /////////////////////////////////////
    setup_motor();

    /////////////////////////////////////
    ///       Sensor Setup         //////
    /////////////////////////////////////
    setup_ToF();

    /////////////////////////////////////
    ///    Deadband Calibration    //////
    /////////////////////////////////////
    // FIXED: Use measured deadband value
    // If you want to skip auto-calibration and use fixed value:
    // deadband = 80;  // Typical for small DC motors
    // Serial.println("Using fixed deadband: 80");

    // Or run auto-calibration:
    deadBand();  // This will measure and set deadband automatically
    Serial.print("Deadband calibrated: "); Serial.println(deadband);

    // Safety override: prevent excessive deadband
    if (deadband > 150) {
        Serial.println("WARNING: Measured deadband too large, capping at 100");
        deadband = 100;
    }

    // Initialize motor off
    MotorSpeed = 0;
    MotorDirection = 1;
    SetMotorControl();

    /////////////////////////////////////
    ///      PID Configuration     //////
    /////////////////////////////////////
    // FIXED: Proper configuration order!
    // 1. Set sample time FIRST
    myPID.SetSampleTime(SampleTime);
    Serial.print("PID Sample Time: "); Serial.print(SampleTime); Serial.println("ms");

    // 2. Set output limits
    myPID.SetOutputLimits(umin, umax);
    Serial.print("PID Output Limits: "); Serial.print(umin); Serial.print(" to "); Serial.println(umax);

    // 3. Set initial tunings
    myPID.SetTunings(Kp, Ki, Kd);
    Serial.print("PID Initial Gains - Kp:"); Serial.print(Kp);
    Serial.print(", Ki:"); Serial.print(Ki);
    Serial.print(", Kd:"); Serial.println(Kd);

    // 4. Start in MANUAL mode (will switch to AUTOMATIC on sync)
    myPID.SetMode(MANUAL);
    Serial.println("PID initialized in MANUAL mode (waiting for sync)");

    /////////////////////////////////////
    /// Publish Initial Parameters  ////
    /////////////////////////////////////
    Serial.println("Waiting for MQTT connection to stabilize...");
    delay(3000);

    // Check if client is connected before publishing
    int attempts = 0;
    while (!client.connected() && attempts < 10) {
        Serial.print("MQTT not connected, waiting... attempt ");
        Serial.println(attempts + 1);
        delay(1000);
        attempts++;

        if (attempts >= 5) {
            // Try to reconnect
            Serial.println("Attempting MQTT reconnection...");
            if (client.connect(carro.c_str())) {
                Serial.println("MQTT reconnected successfully");
            }
        }
    }

    if (client.connected()) {
        Serial.println("MQTT connected, publishing initial parameters...");
        Serial.print("  Kp="); Serial.print(Kp);
        Serial.print(", Ki="); Serial.print(Ki);
        Serial.print(", Kd="); Serial.print(Kd);
        Serial.print(", x_ref="); Serial.println(x_ref);

        bool pub1 = client.publish("trenes/carroD/p/status", String(Kp).c_str());
        delay(100);
        bool pub2 = client.publish("trenes/carroD/i/status", String(Ki).c_str());
        delay(100);
        bool pub3 = client.publish("trenes/carroD/d/status", String(Kd).c_str());
        delay(100);
        bool pub4 = client.publish("trenes/carroD/ref/status", String(x_ref).c_str());

        Serial.print("Publish results: Kp="); Serial.print(pub1);
        Serial.print(", Ki="); Serial.print(pub2);
        Serial.print(", Kd="); Serial.print(pub3);
        Serial.print(", Ref="); Serial.println(pub4);

        if (pub1 && pub2 && pub3 && pub4) {
            Serial.println("✓ All initial parameters published successfully");
        } else {
            Serial.println("⚠ Some initial parameters failed to publish - will retry in main loop");
        }
    } else {
        Serial.println("⚠ MQTT connection failed - initial parameters will be published when connection is established");
    }

    tiempo_inicial = millis();

    Serial.println("==============================================");
    Serial.println("  Setup Complete! Ready for experiments.");
    Serial.println("  Send 'True' to trenes/sync to start PID control");
    Serial.println("==============================================");
}
