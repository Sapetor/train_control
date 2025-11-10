/*
 * FIXED VERSION - Communication Module
 *
 * Key Fixes:
 * 1. Added pid_params_changed flag to signal main loop
 * 2. Only SetTunings when parameters actually change
 * 3. Improved error handling and sync logic
 */

///////////////////////////////CONFIGURACION WIFI////////////////
void setup_wifi() {
    WiFi.mode(WIFI_STA);
    esp_wifi_set_ps(WIFI_PS_NONE);
    Serial.println();
    Serial.print("Connecting to ");
    Serial.println(ssid);

    WiFi.useStaticBuffers(true);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());
}

void setup_mqtt() {
    client.setServer(mqtt_server, 1883);
    client.setCallback(callback);

    if (!client.connected()) {
        reconnect();
        Serial.println("Sub a los topicos ");
    }
    client.loop();
}

void reconnect() {
    // Loop until we're reconnected
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        if (client.connect(carro.c_str())) {
            Serial.println(" connected!");

            // LISTA SUBSCRIPCIONES
            client.subscribe(trenesp);
            client.subscribe(trenesi);
            client.subscribe(trenesd);
            client.subscribe(trenesp_v);
            client.subscribe(trenesi_v);
            client.subscribe(trenesd_v);
            client.subscribe(trenesestado);
            client.subscribe("trenes/ref");
            client.subscribe("trenes/etha");
            client.subscribe("trenes/u_lim");
            client.subscribe("trenes/carroL/v_lider");
            client.subscribe("trenes/carroL/vref");
            client.subscribe("trenes/sync");
            client.subscribe(trenessampletime);
            client.subscribe(trenestransmision);
            client.subscribe("trenes/carroD/request_params");
        } else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" try again in 5 seconds");
            delay(5000);
        }
    }
}

/* MQTT Callback - FIXED VERSION */
void callback(char* topic, byte* payload, unsigned int length) {
    String mensaje;
    for (int i = 0; i < length; i++) {
        char nuevo = (char)payload[i];
        mensaje.concat(nuevo);
    }

    ////////////////////////////////
    // SYNC COMMAND ////////////////
    ////////////////////////////////
    if (String(topic) == "trenes/sync") {
        if (String(mensaje) == "True") {
            tiempo_inicial = millis();
            Serial.println("Sync Recibido");
            flag = false;

            // FIXED: Only set mode to AUTOMATIC when starting
            // Don't keep switching modes in main loop
            myPID.SetMode(AUTOMATIC);

            // Reset outputs to prevent jumps
            u_distancia = 0;
            u_velocidad = 0;
            MotorDirection = 1;  // Default forward
        }
        else if (String(mensaje) == "False") {
            Serial.println("Detener");
            flag = true;
            start = false;

            // Stop motor
            MotorSpeed = 0;
            SetMotorControl();

            // Disable PID
            myPID.SetMode(MANUAL);

            // Reset outputs
            u_distancia = 0;
            u_velocidad = 0;
        }
    }

    ////////////////////////////////
    // PID PARAMETERS //////////////
    ////////////////////////////////
    // FIXED: Set flag instead of calling SetTunings directly
    // This prevents integrator reset every time MQTT message arrives

    if (strcmp(topic, trenesp) == 0) {
        double new_Kp = mensaje.toFloat();
        if (new_Kp != Kp) {  // Only update if changed
            Kp = new_Kp;
            pid_params_changed = true;  // Signal main loop to update
            client.publish("trenes/carroD/p/status", String(Kp).c_str());
            Serial.print("Kp updated: "); Serial.println(Kp);
        }
    }

    if (strcmp(topic, trenesi) == 0) {
        double new_Ki = mensaje.toFloat();
        if (new_Ki != Ki) {  // Only update if changed
            Ki = new_Ki;
            pid_params_changed = true;  // Signal main loop to update
            client.publish("trenes/carroD/i/status", String(Ki).c_str());
            Serial.print("Ki updated: "); Serial.println(Ki);
        }
    }

    if (strcmp(topic, trenesd) == 0) {
        double new_Kd = mensaje.toFloat();
        if (new_Kd != Kd) {  // Only update if changed
            Kd = new_Kd;
            pid_params_changed = true;  // Signal main loop to update
            client.publish("trenes/carroD/d/status", String(Kd).c_str());
            Serial.print("Kd updated: "); Serial.println(Kd);
        }
    }

    if (strcmp(topic, trenesp_v) == 0) {
        Kp_v = mensaje.toFloat();
    }

    if (strcmp(topic, trenesi_v) == 0) {
        Ki_v = mensaje.toFloat();
    }

    if (strcmp(topic, trenesd_v) == 0) {
        Kd_v = mensaje.toFloat();
    }

    ////////////////////////////////
    // OTHER PARAMETERS ////////////
    ////////////////////////////////
    if (strcmp(topic, "trenes/etha") == 0) {
        etha = mensaje.toFloat();
    }

    if (strcmp(topic, "trenes/u_lim") == 0) {
        umax = mensaje.toInt();
        umin = -umax;
        myPID.SetOutputLimits(umin, umax);  // Update PID limits
        Serial.print("Output limits updated: ±"); Serial.println(umax);
    }

    if (strcmp(topic, "trenes/carroL/v_lider") == 0) {
        v_lider = mensaje.toFloat();
    }

    if (strcmp(topic, "trenes/carroL/vref") == 0) {
        v_ref = mensaje.toFloat();
    }

    if (strcmp(topic, "trenes/ref") == 0) {
        double new_ref = mensaje.toFloat();
        if (new_ref != x_ref) {  // Only update if changed
            x_ref = new_ref;
            client.publish("trenes/carroD/ref/status", String(x_ref).c_str());
            Serial.print("Reference updated: "); Serial.println(x_ref);
        }
    }

    if (strcmp(topic, trenessampletime) == 0) {
        int new_SampleTime = mensaje.toInt();
        if (new_SampleTime != SampleTime && new_SampleTime > 0) {
            SampleTime = new_SampleTime;
            myPID.SetSampleTime(SampleTime);
            Serial.print("Sample time updated: "); Serial.print(SampleTime); Serial.println("ms");
            Serial.println("WARNING: Changing sample time requires re-tuning Ki and Kd!");
        }
    }

    if (strcmp(topic, trenestransmision) == 0) {
        t_envio = mensaje.toInt();
    }

    if (strcmp(topic, "trenes/carroD/request_params") == 0) {
        Serial.println("Parameter request received - publishing current values");
        client.publish("trenes/carroD/p/status", String(Kp).c_str());
        delay(10);
        client.publish("trenes/carroD/i/status", String(Ki).c_str());
        delay(10);
        client.publish("trenes/carroD/d/status", String(Kd).c_str());
        delay(10);
        client.publish("trenes/carroD/ref/status", String(x_ref).c_str());
        Serial.println("Current parameters published on request");
    }
}
