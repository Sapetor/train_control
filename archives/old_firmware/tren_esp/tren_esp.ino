
#include <PID_v1_bc.h>
#include <WiFi.h>
#include <PubSubClient.h>

#include <Wire.h>   // ???
#include <VL53L0X.h>  // Pololu 1.0.2

#include <esp_wifi.h>




  
////////////////////////////////////////////
///////////////////////////////////////////
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
char trenestest[] = "trenes/carroD/test";     // Donde se envian los datos a analizar separados por ","
char trenessampletime[] = "trenes/carroD/ts"; // Lista para modificar el tiempo de sampleo del PID
char trenestransmision[] = "trenes/envio";    // Lista para modificar el tiempo de transmision
int t_envio = 50;                             // Tiempo de transmision por defecto;
///////////////////////////////////////////
/////////////////////////////////////////// 


int yy=0;  // coordenadas obtenidas por sensor ADNS3080 (dead reckoning)
double temp_cal;
double scale; // escalamiento de cuentas ADNS a cm 
double medi = 10;
double xx = 10;


// filtro ToF
int INDEX = 0;
int VALUE = 0;
int SUM = 0;
int READINGS[10];
double AVERAGED = 0;


//moving avg
int arrNumbers[3] = {0};

int pos = 0;
float newAvg = 0;
float oldAvg = 0;
int newSum = 0;
long sum = 0;
int len = sizeof(arrNumbers) / sizeof(int);


///////////////////////////////////////
//     Configuración MQTT   ///////////
///////////////////////////////////////
const char* ssid = "TICS322";//"Quanser_UVS"; //"Xiaomi13apr";//"SAPOSAPO";
const char* password = "esp32esp32";//"UVS_wifi";//"110725011";


///////////////////////////////////////
//     Configuración MQTT & UDP   ///////////
///////////////////////////////////////
const char* mqtt_server = "192.168.137.1"; //"10.107.182.149";//"192.168.137.1";//"192.168.100.65";
const int udpPort = 5555;                   //puerto de envio UDP*
String estado;        //variables para los mensajes publicados en MQTT

WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;  
char msg[128];
WiFiUDP udp;



////////////////////////////////////////////////////
//          Configuración motor DC      ////////////
////////////////////////////////////////////////////
const int STBY = 7;
const int Control_fwd = 8;                //  Pin AIN1  [Control del sentido de rotaciÃ³n +]
const int Control_back = 18;            //  Pin AIN2   [Control del sentido de rotaciÃ³n -]
const int Control_v = 17;                 //  Pin PWMA    [Control de la velocidad de rotaciÃ³n]
int MotorSpeed = 0;                   // Velocidad del motor  0..1024
int MotorDirection = 1;               // Avanzar (1) o Retroceder (0)

////////////////////////////////////////////////
//         Variables para Sensor Distancia /////
////////////////////////////////////////////////
VL53L0X SensorToF;
double distancia = 25;
double old_d = 0;                         
double old = 0;  
double t_distancia = 0;
double t_old;
double t1; // para temporizar la medición de la velocidad
double t2;

////////////////////////////////////////////
//      Varaibles para código general //////
////////////////////////////////////////////
int dead = 1;     // flag buscar zona muerta
int deadband = 300;     //valor de deadband inicial en caso de no querer buscar deadband
int tiempo_inicial = 0;
bool flag = true; //flag para sincronizar
bool start = false; // variable para iniciar la prueba

////////////////////////////////////////////
// Variables y parametros PIDs /////////////
////////////////////////////////////////////
double v_lider = 0, mierror;
float v_medida = 0;
float v_ref = 0;
double x_ref = 10;
double u_distancia;                         //Actuacion calculada por distancia                           
double u_velocidad;                         //Actuacion calculada por velocidad
double u;                                   //Actuacion ponderada
double u_send; //Actuacion para ser enviada sin zona muerta

int umin = -1024, umax = 1024;//C5 800
double Kp =0, Ki = 0, Kd = 0;             //Ganancias PID control de distancia
double Kp_v = 10, Ki_v = 1, Kd_v = 0;       //Ganancias PID control de velocidad   
int SampleTime = 50;                       //Tiempo de muestreo ambos controladores
double etha = 0.5;
int Frequency = 100;
int PreviousFrequency;
int deadband1 = 0;
double alpha = 0; // constante para el control con velocidad lider

double N = 10; //Constante Filtro Derivativa D(s)=s/(1+s/N)
double error_distancia;
double error_velocidad;
double ponderado;
double rf = 0;
int lim = 10;
PID myPID(&error_distancia, &u_distancia, &rf, Kp, Ki, Kd, DIRECT);


void loop() {
    
    // //Verificación de conexion MQTT
    if (!client.connected()) {
        reconnect();
        estado = String(carro) + " Reconectando";
        estado.toCharArray(msg, estado.length() + 1);                                                                           
        client.publish(trenesestado, msg);
    }
    
    client.loop();
    //Serial.println("hola");
    if(flag==false){   // Envia desfase para sincronizar datos de la prueba
        String delta = String((millis()-tiempo_inicial)*0.001);
        delta.toCharArray(msg, delta.length() + 1);                                                                           
        client.publish(trenesdesfase, msg);
        flag = true;
        start = true;
        Serial.println("Sync!");
    }  // Da comienzo a la prueba
    
    else if (start)
    {   
        // Si recibe la señal de inicio  
        // Medicion  y Envio de Variables
        // Mediciones  
        xx=medi; // memoria para filtrar medi (medicion de distancia)
        medi=0;
      
              
        old=micros();
        
        //int val = mousecam_read_reg(ADNS3080_PIXEL_SUM);
        //delayMicroseconds(3500);
        for (int i = 0; i < 2 ; i++) {
            
                uint16_t range = SensorToF.readReg16Bit(SensorToF.RESULT_RANGE_STATUS + 10);
                medi=medi+range;
         
          delay(21);  // retardo arbitrario. No cambia mucho la medición del adns3080. Si se lee el registro de movimiento muy seguido entrega 0s pq no ha detectado movimiento.
        }

        medi = medi/2;
        
        Serial.print(medi);
        newSum = movingSum(arrNumbers, &sum, pos, len, medi);
        newAvg = newSum/(float)len;
        Serial.print(" ,");
        //Serial.println(0.7*newAvg+0.3*oldAvg);
        pos++;
        if (pos >= len){
          pos = 0;
        }
        oldAvg = newAvg;
        medi =(0.8*newAvg+0.2*oldAvg)/10;
        Serial.print(medi);
        
        

    
        error_distancia = (x_ref - medi);
        
        Serial.print(" ,");
        Serial.println(error_distancia);


        myPID.SetTunings(Kp, Ki, Kd);
        myPID.SetOutputLimits(umin, umax);
        myPID.Compute();
        myPID.SetSampleTime(SampleTime);
        //ponderado = abs(v_medida);  // error ponderado para evitar oscilación cuando el error es pequenho
        
        //u = (1 - etha) * u_distancia + etha * ( u_velocidad);                   // ponderacion de actuaciones 
        //alpha = 0;
        u =  u_distancia;// + alpha * ( u_velocidad);                   // control nuevo alpha>0, debería mejorar alpha > alpha_min por determinar
        
    
        uint32_t time_now = millis();
        t_old = millis();
        
               estado = String(time_now)+","+String(medi)+","+String(x_ref)+","+String(error_distancia)+","+String(Kp)+","+String(Ki)+","+String(Kd)+","+String(u);
                estado.toCharArray(msg, estado.length() + 1);                                                                           
                
                //Serial.println(estado);
                //client.publish("esp/datos", msg);
                //------------------------------------
                udp.beginPacket(mqtt_server,udpPort);
                udp.printf(msg);      //
                udp.endPacket();
        
        ////////////////////////////////////////////////////////
        //        Rutina del Carro                 /////////////
        ////////////////////////////////////////////////////////
    
        if ((medi > 200))   // si no hay nada enfrente: detenerse o desacelerar
        {
            if (MotorSpeed < 200) MotorSpeed = MotorSpeed -  10 ; 
            else MotorSpeed = 0; 
            myPID.SetMode(MANUAL); // para que no siga integrando
            
        }
  
        else
        {
            if (u < -lim)  //lim es un valor arbitrario donde se desea que el carro no se mueva si |u|<=lim
            {
                MotorDirection = 0;
                MotorSpeed = int(-u + deadband ); //- 40);
            }
            else if (u > lim)
            {
                MotorDirection = 1;
                MotorSpeed = int(u + deadband ); //- 40);
            }
  
            if (((u >= -lim)) && ((u <= lim)))
            {
                myPID.SetMode(MANUAL);            // apaga el PID de distancia
                
                MotorSpeed = 0;
                if (u > 0)  MotorDirection = 1;
                else  MotorDirection = 0;
            }
  
            if (((u >= -lim) && (u <= lim) && (abs(ponderado) <= 0.75))) // detener si estamos en reposo
            {
                MotorSpeed = 0;
                if (u < 0)  MotorDirection = 1;
                else  MotorDirection = 0;
            }
            if( (medi < 200)){ // condicion para revivir el PID
                myPID.SetMode(AUTOMATIC);
                
            }        
        }
        
        int test_sin_control=0;
        if (test_sin_control)
        {
          myPID.SetMode(MANUAL);            // apaga el PID de distancia
          
          MotorSpeed=0;
        }
        
        
        SetMotorControl();
    }
}









