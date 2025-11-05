void setup_motor()
{
  pinMode(STBY, OUTPUT);     // STBY - Definicion Pin como salida
  digitalWrite(STBY, HIGH);
  pinMode(Control_fwd, OUTPUT);     // 1A - Definicion Pin como salida
  pinMode(Control_back, OUTPUT);    // 2A - Definicion Pin como salida
  pinMode(Control_v, OUTPUT);       // 1,2 EN - Definicion Pin como salida
  digitalWrite(Control_v, HIGH);    // Motor off - O Volts (HIGH = 0, por algÃºn motivo)
  ledcAttach(Control_v,100,10);//Freq a 100 Hz ESP32 resolución 10 bits
}

void SetMotorControl()
{
    if (MotorDirection == 1)            //Avanzar
    {
        digitalWrite(Control_fwd, LOW);
        digitalWrite(Control_back, HIGH);
    }
    else                                //Retroceder
    {
        digitalWrite(Control_fwd, HIGH);
        digitalWrite(Control_back, LOW);
    }
    
    ledcWrite(Control_v, MotorSpeed); // esp32
}