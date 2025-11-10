///////////////////////////////CONFIGURACION WIFI////////////////
void setup_wifi() {
  WiFi.mode(WIFI_STA);
  esp_wifi_set_ps(WIFI_PS_NONE);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  // WiFi.begin(ssid, password);

  // //while (WiFi.status() != WL_CONNECTED) {
  // while (WiFi.waitForConnectResult() != WL_CONNECTED) {
  //   delay(500);
  //   Serial.print(".");
  //   WiFi.begin(ssid, password);
  // }
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
void setup_mqtt(){
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
        }
        else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" try again in 5 seconds");
            // Wait 5 seconds before retrying
            delay(5000);
        }
    }
}

/* MQTT Callback */
void callback(char* topic, byte* payload, unsigned int length) {
    String mensaje;
    for (int i = 0; i < length; i++) {
        char nuevo = (char)payload[i];
        mensaje.concat(nuevo);
    }
    ////////////////////////////////
    // QUE HACE AL RECIBIR DATOS ///
    ////////////////////////////////
  
    if (String(topic) == "trenes/sync") {
        if (String(mensaje)=="True") {
            tiempo_inicial = millis();
            Serial.println("Sync Recibido");
            flag = false;
            myPID.SetMode(AUTOMATIC);            // prende el PID de distancia  
            
        }
        else if (String(mensaje)=="False"){
            Serial.println("Detener");
            flag = true;
            start = false;
            MotorSpeed = 0;
            SetMotorControl();
            myPID.SetMode(MANUAL);            // apaga el PID de distancia  
            
            u_distancia = 0;
            u_velocidad = 0; 
        }
    }
    if (strcmp(topic ,trenesp) == 0) {
        Kp = mensaje.toFloat();
        client.publish("trenes/carroD/p/status", String(Kp).c_str());
    }
    if (strcmp(topic , trenesi) == 0) {
        Ki = mensaje.toFloat();
        client.publish("trenes/carroD/i/status", String(Ki).c_str());
    }
    if (strcmp(topic , trenesd) == 0) {
        Kd = mensaje.toFloat();
        client.publish("trenes/carroD/d/status", String(Kd).c_str());
    }
    if (strcmp(topic ,trenesp_v) == 0) {
        Kp_v = mensaje.toFloat();
    }
    if (strcmp(topic , trenesi_v) == 0) {
        Ki_v = mensaje.toFloat();
    }
    if (strcmp(topic , trenesd_v) == 0) {
        Kd_v = mensaje.toFloat();
    }
    if (strcmp(topic , "trenes/etha") == 0) {
        etha = mensaje.toFloat();
    }
    if (strcmp(topic , "trenes/u_lim") == 0) {
        umax = mensaje.toInt();
        umin = -umax;
    }
    if (strcmp(topic , "trenes/carroL/v_lider") == 0) {
        v_lider = mensaje.toFloat();
    }
    if (strcmp(topic , "trenes/carroL/vref") == 0) {
        v_ref = mensaje.toFloat();
    }
    if (strcmp(topic , "trenes/ref") == 0) {
        x_ref = mensaje.toFloat();
        client.publish("trenes/carroD/ref/status", String(x_ref).c_str());
    }
    if (strcmp(topic , trenessampletime) == 0) {
        SampleTime = mensaje.toInt();
    }
    if (strcmp(topic , trenestransmision) == 0) {
        t_envio = mensaje.toInt();
    }
    if (strcmp(topic , "trenes/carroD/request_params") == 0) {
        Serial.println("Parameter request received - publishing current values");
        client.publish("trenes/carroD/p/status", String(Kp).c_str());
        client.publish("trenes/carroD/i/status", String(Ki).c_str());
        client.publish("trenes/carroD/d/status", String(Kd).c_str());
        client.publish("trenes/carroD/ref/status", String(x_ref).c_str());
        Serial.println("Current parameters published on request");
    }
}