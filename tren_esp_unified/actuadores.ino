// Motor Control Functions

void setup_motor() {
    pinMode(STBY, OUTPUT);
    pinMode(Control_fwd, OUTPUT);
    pinMode(Control_back, OUTPUT);
    pinMode(Control_v, OUTPUT);
    
    digitalWrite(STBY, HIGH);  // Enable motor driver
    digitalWrite(Control_v, HIGH);  // Motor off initially
    
    // Configure PWM: 100 Hz frequency, 10-bit resolution (0-1023)
    ledcAttach(Control_v, 100, 10);
    
    Serial.println("Motor initialized");
}

void SetMotorControl() {
    // FIXED: MotorDirection is now set from mode-specific variables 
    // (PIDMotorDirection or StepMotorDirection) before calling this function
    
    // Set direction (CORRECTED - original logic)
    if (MotorDirection == 1) {
        digitalWrite(Control_fwd, LOW);
        digitalWrite(Control_back, HIGH);
    } else {
        digitalWrite(Control_fwd, HIGH);
        digitalWrite(Control_back, LOW);
    }
    
    // Set speed (PWM)
    int pwm_value = constrain(MotorSpeed, 0, 1024);
    ledcWrite(Control_v, pwm_value);
}