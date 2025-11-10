void setup() {

    //WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG,0);//disable brownout detector
    Serial.begin(115200);
    Serial.println("setup!");
    setup_wifi();
    setup_mqtt();
    /////////////////////////////////////
    ///       Inicio Motor         //////
    /////////////////////////////////////
    setup_motor();
    ///////////////////////////////////////////
    //         Inicio de Sensores           ///
    ///////////////////////////////////////////
    setup_ToF();
    deadBand();
    MotorSpeed = 0;   
    SetMotorControl();
    old = 0;
    Serial.println("Setup Completado");
    String ini = String(11111111, 2);// + ", " + String(millis());
    ini.toCharArray(msg, ini.length() + 1);                    // Datos enviados para analizar controlador
    client.publish("trenes/carroL/v_lider", msg);
  
    myPID.SetMode(AUTOMATIC);
    myPID.SetOutputLimits(umin, umax);
    myPID.SetSampleTime(SampleTime);

    // Publish initial PID parameter values to dashboard
    Serial.println("Waiting for MQTT connection to stabilize...");
    delay(3000); // Wait even longer for MQTT connection

    // Check if client is connected before publishing
    int attempts = 0;
    while (!client.connected() && attempts < 10) {
        Serial.print("MQTT not connected, waiting... attempt "); Serial.println(attempts + 1);
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
        Serial.print("Kp="); Serial.print(Kp);
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

        if(pub1 && pub2 && pub3 && pub4) {
            Serial.println("All initial parameters published successfully");
        } else {
            Serial.println("Some initial parameters failed to publish - will retry in main loop");
        }
    } else {
        Serial.println("MQTT connection failed - initial parameters will be published when connection is established");
    }

    tiempo_inicial = millis();
 } 
    




