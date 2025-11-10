// ToF Sensor Setup

void setup_ToF() {
    Serial.println("Initializing ToF sensor...");
    
    // Initialize I2C with custom pins (SDA=10, SCL=9)
    Wire.begin(10, 9);
    
    SensorToF.setTimeout(500);
    while (!SensorToF.init()) {
        Serial.println("Failed to detect and initialize sensor!");
        delay(1000);
    }
    
    // Configure ToF sensor for optimal performance
    SensorToF.setSignalRateLimit(0.25);
    SensorToF.setMeasurementTimingBudget(22000);
    SensorToF.startContinuous();
    
    Serial.println("ToF sensor ready");
}