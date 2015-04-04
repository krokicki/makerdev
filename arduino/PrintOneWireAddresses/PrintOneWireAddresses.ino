#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS 5


/*
0=28 ff 6b 56 54 14 00 ca 
1=28 ff 97 56 54 14 00 4d 
2=28 ff d7 55 77 04 00 b0 

0=28 ff 36 1b 6b 04 00 a3
*/


OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

int numDevices = 0;

void setup(void)
{
  Serial.begin(57600);

  Serial.println("Searching for devices...");
  sensors.begin();
  
  numDevices = sensors.getDeviceCount();
  Serial.print("Detected ");
  Serial.print(numDevices);
  Serial.println(" devices:");  
 
  for(int i=0; i<numDevices; i++) {
    DeviceAddress deviceAddress;
    sensors.getAddress(deviceAddress, i);
    Serial.print(i);
    Serial.print("=");
    for(int j=0; j<8; j++) {
      String s = String(deviceAddress[j], HEX); 
      if (s.length()==1) {
        Serial.print("0"); 
      }
      Serial.print(s);
      Serial.print(" ");
    }
    Serial.println();
    
  }
}

void loop(void)
{ 
  
  sensors.requestTemperatures();
  for(int i=0; i<numDevices; i++) {
    if (i>0) Serial.print("\t");
    Serial.print(sensors.getTempCByIndex(i));   
  }
  Serial.println();
  delay(2000); 
}
