#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS 2

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

void setup(void)
{
  Serial.begin(9600);
  Serial.println("Searching for devices...");
  sensors.begin();
  
  int numDevices = sensors.getDeviceCount();
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
  for(int i=0; i<numDevices; i++) {
    if (i>0) Serial.print("\t");
    Serial.print(sensors.getTempCByIndex(i));   
  }
  Serial.println();
  delay(2000); 
}
