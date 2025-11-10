void deadBand()
{
  uint16_t range=0;
  range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);
  medi = range;

  int Frequencies[]={200};
  int len2= sizeof(Frequencies) / sizeof(int);

  for (int i = 0; i < len2; i++) {
      dead=1;
      Frequency=Frequencies[i];
      //ledcSetup(Control_v, Frequency, 10);
      ledcAttach(Control_v,Frequency,10);
      //Serial.println("hola");
      while (dead)    //---------------------------------------
      {      
      range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);
      if (abs(medi - range) < 10){
        MotorSpeed += 1;
        SetMotorControl();
        delay(40);
        //Serial.println("hola");
        range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);
        
        if (abs(medi - range) > 0.8) 
          {   
              
              deadband = MotorSpeed;  //ACA ENVIAR EL DATO DE LA DEADBAND*************************************************************************************************************************
              MotorSpeed = 0;
              SetMotorControl();
              Serial.print("DeadBand Listo!! ");Serial.print(Frequencies[i]); Serial.print("[Hz], DeadBand en: "); Serial.println(deadband);
                  
              
              delay(1000);
              
              dead=0;
              
          }
        }
      }
  }
  Serial.println(Frequency);
}
