void setup_ToF(){
  // CONFIGURACION SENSOR ToF ////////////////////////////////////                         
  Wire.begin(10,9);                                                       ///
  SensorToF.setTimeout(500);                                             ///
  while (!SensorToF.init())                                                 ///
  {                                                                   ///
    Serial.println("Failed to detect and initialize sensor!");        ///                                                    ///
    delay(1000); 
  }                                                                   ///
  SensorToF.setSignalRateLimit(0.25);                                    ///
  SensorToF.setMeasurementTimingBudget(22000);                           ///
  SensorToF.startContinuous(); //toma medidas cada {Argumento} ms     ///
/////////////////////////////////////////////////////////////////////////
  }


float movingSum(int *ptrArrNumbers, long *ptrSum, int pos, int len, int nextNum)
{
  //Subtract the oldest number from the prev sum, add the new number
  *ptrSum = *ptrSum - ptrArrNumbers[pos] + nextNum;
  //Assign the nextNum to the position in the array
  ptrArrNumbers[pos] = nextNum;
  //return the Sum
  return *ptrSum;
}  
