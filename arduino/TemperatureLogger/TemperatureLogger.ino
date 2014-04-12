// Data Logger
// Improvements upon the default Stalker logger example:
// - Using flash memory for all strings
// - Battery status logging
// - Seeeduino onboard temperature logging
// - OneWire DS18B20 external temperature logging
//
// Use: Arduino Pro or Pro Mini (3.3V, Mhz) w/ ATmega328

#include <avr/sleep.h>
#include <avr/power.h>
#include <Wire.h>
#include <DS3231.h>
#include <Fat16.h>
#include <Fat16util.h>
#include <Battery.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <EEPROM.h>

//#define DEBUG

#define PgmLog(x) Log_P(PSTR(x))
#define PgmLogChar(x) LogChar(x)
#define PgmLogDec(x) LogDec(x)
#define PgmLogDouble(x) LogDouble(x)
#define PgmLogln(x) Logln_P(PSTR(x))
#define PgmError(x) Error_P(PSTR(x))

//#define LOOP_INTERVAL_SEC 300 // 5 minutes
#define LOOP_INTERVAL_SEC 5 

//The following code is taken from sleep.h as Arduino Software v22 (avrgcc) in w32 does not have the latest sleep.h file
#define sleep_bod_disable() \
{ \
  uint8_t tempreg; \
  __asm__ __volatile__("in %[tempreg], %[mcucr]" "\n\t" \
                       "ori %[tempreg], %[bods_bodse]" "\n\t" \
                       "out %[mcucr], %[tempreg]" "\n\t" \
                       "andi %[tempreg], %[not_bodse]" "\n\t" \
                       "out %[mcucr], %[tempreg]" \
                       : [tempreg] "=&d" (tempreg) \
                       : [mcucr] "I" _SFR_IO_ADDR(MCUCR), \
                         [bods_bodse] "i" (_BV(BODS) | _BV(BODSE)), \
                         [not_bodse] "i" (~_BV(BODSE))); \
}

// Data wire is plugged into port 2 on the Arduino
#define ONE_WIRE_BUS 6
#define LED_PIN 13

DS3231 RTC; //Create RTC object for DS3231 RTC come Temp Sensor 
DateTime interruptTime;
SdCard card;
Fat16 file;
Battery battery;
OneWire ds(ONE_WIRE_BUS);
DallasTemperature sensors(&ds);

const int numDevices = 20;
char* idStrs[] = {
"2881b859050000cc",
"28f7245a050000f8",
"28a3065a05000071",
"28c05766050000e9",
"28e8e259050000b1",
"280e0a5a05000046",
"28b7db59050000cc",
"28f6d5590500002c",
"2826cc5905000067",
"28373c5a05000025",
"285e27d10400009a",
"289f0ad0040000a9",
"28a12cd1040000bc",
"287f48d0040000ea",
"28913fd0040000ec",
"28bdadd004000013",
"28df11d0040000d0",
"28bd4cd004000004",
"28a65dd004000016",
"283081d00400006a"
};

byte ids[numDevices][8];

void setup () {
    /* Initialize INT0 pin for accepting interrupts */
    PORTD |= 0x04; // set pin 2 to HIGH 
    DDRD &=~ 0x04; // set pin 2 to OUTPUT
    
    pinMode(4, INPUT); // control SD card power
    pinMode(LED_PIN, OUTPUT);
    Wire.begin();    
    RTC.begin();

    #ifdef DEBUG 
      Serial.begin(57600);
    #endif
    
    attachInterrupt(0, INT0_ISR, LOW); // Only LOW level interrupt can wake up from PWR_DOWN
    set_sleep_mode(SLEEP_MODE_PWR_DOWN);
 
    // Enable Interrupt 
    DateTime now = RTC.now();
    interruptTime = DateTime(now.get() + LOOP_INTERVAL_SEC);
    
    PgmLogDec(now.year());
    PgmLog("/");
    PgmLogDec(now.month());
    PgmLog("/");
    PgmLogDec(now.date());
    PgmLog(",");
    PgmLogDec(now.hour());
    PgmLog(":");
    PgmLogDec(now.minute());
    PgmLog(":");
    PgmLogDec(now.second());
    PgmLog(",");
    PgmLogln("Begin");
}

void loop () {
  
    ledOn();
    
    // Parse device addresses
    for(int i=0; i<numDevices; i++) {
      for(int j=0; j<8; j++) {
          char strPart[3];
          strPart[0] = idStrs[i][j*2];
          strPart[1] = idStrs[i][j*2+1];
          strPart[2] = NULL;
          long unsigned int id = strtoul(strPart, NULL, 16);
          ids[i][j] = id;
      }
    }

//    #ifdef DEBUG 
//      for(int i=0; i<numDevices; i++) {
//        if (i>0) Serial.print("\t");
//        Serial.print(idStrs[i]);
//      }
//      Serial.println();
//    #endif
    
    sensors.begin();
      
    // Read time from RTC
    DateTime now = RTC.now();
  
    // Read battery status
    battery.update();
    float voltage = battery.getVoltage();
    int percentage = battery.getPercentage();
    char* chargeStatus = battery.getChStatus();
    
    // Read built-in temperature
    RTC.convertTemperature();
    float internalTemp = RTC.getTemperature();
    
    // Initialize the SD card
    if (!card.init()) PgmError("card.init");
    if (!Fat16::init(&card)) PgmError("Fat16::init");
    file.writeError = false; // clear write error
    
    String filenameStr = "";
    filenameStr += now.year();
    if (now.month() < 10) {
      filenameStr += "0";
    }
    filenameStr += now.month();
    filenameStr += ".LOG";
      
    char filename[filenameStr.length()+1];
    filenameStr.toCharArray(filename, sizeof(filename));

    // O_CREAT - create the file if it does not exist
    // O_APPEND - seek to the end of the file prior to each write
    // O_WRITE - open for write
    // O_TRUNC - truncate the file
    
    //if (!file.open(filename, O_CREAT | O_TRUNC | O_WRITE)) {
    if (!file.open(filename, O_CREAT | O_APPEND | O_WRITE)) {
        PgmError("Error opening file");
    }
    
    PgmLogDec(now.year());
    PgmLog("/");
    PgmLogDec(now.month());
    PgmLog("/");
    PgmLogDec(now.date());
    PgmLog(",");
    PgmLogDec(now.hour());
    PgmLog(":");
    PgmLogDec(now.minute());
    PgmLog(":");
    PgmLogDec(now.second());
    PgmLog(",");
    PgmLogDouble(voltage);
    PgmLog(",");
    PgmLogDec(percentage);
    PgmLog(",");
    Log(chargeStatus);
    PgmLog(",");
    PgmLogDouble(internalTemp);
    
    for(int i=0; i<numDevices; i++) {
      PgmLog(",");
      PgmLogDouble(sensors.getTempC(ids[i]));   
    }
    
    Logln("");
    
    if (!file.close()) {
      PgmError("error closing file");
    }
    
    ledOff();
    
    RTC.clearINTStatus(); //This function call is a must to bring /INT pin HIGH after an interrupt.
    RTC.enableInterrupts(interruptTime.hour(),interruptTime.minute(),interruptTime.second());    // set the interrupt at (h,m,s)
    attachInterrupt(0, INT0_ISR, LOW);  //Enable INT0 interrupt (as ISR disables interrupt). This strategy is required to handle LEVEL triggered interrupt
    
    //\/\/\/\/\/\/\/\/\/\/\/\/Sleep Mode and Power Down routines\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
            
    //Power Down routines
    cli(); 
    sleep_enable();      // Set sleep enable bit
    sleep_bod_disable(); // Disable brown out detection during sleep. Saves more power
    sei();
        
    delay(10); //This delay is required to allow print to complete
    //Shut down all peripherals like ADC before sleep. Refer Atmega328 manual
    power_all_disable(); //This shuts down ADC, TWI, SPI, Timers and USART
    sleep_cpu();         // Sleep the CPU as per the mode set earlier(power down)  
    sleep_disable();     // Wakes up sleep and clears enable bit. Before this ISR would have executed
    power_all_enable();  //This shuts enables ADC, TWI, SPI, Timers and USART
    delay(10); //This delay is required to allow CPU to stabilize
    
    //\/\/\/\/\/\/\/\/\/\/\/\/Sleep Mode and Power Saver routines\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

} 

float getOneWireTemp() {
  
  float celsius = NAN;
  
  int c = 0;
  while (1) {
    c++;
    byte present = 0;
    byte data[12];
    byte addr[8];
    
    if (!ds.search(addr)) {
      ds.reset_search();
      if (isnan(celsius)) {
        //PgmError("OneWire temperature sensor is not connected");
        return NAN;
      }   
      return celsius;
    }
    
    if (OneWire::crc8(addr, 7) != addr[7]) {
      PgmError("OneWire CRC is not valid!");
      return NAN;
    }
   
    // the first ROM byte indicates which chip
    if (addr[0] != 0x28) {
      PgmError("OneWire device is not a DS18B20");
      return NAN;  
    }
    
    ds.reset();
    ds.select(addr);
    ds.write(0x44, 1);        // start conversion, with parasite power on at the end
    delay(1000);     // maybe 750ms is enough, maybe not
    // we might do a ds.depower() here, but the reset will take care of it.
    present = ds.reset();
    ds.select(addr);    
    ds.write(0xBE); // Read Scratchpad
    for (byte i = 0; i < 9; i++) { // we need 9 bytes
      data[i] = ds.read();
    }
      
    // Convert the data to actual temperature
    // because the result is a 16 bit signed integer, it should
    // be stored to an "int16_t" type, which is always 16 bits
    // even when compiled on a 32 bit processor.
    int16_t raw = (data[1] << 8) | data[0];
    byte cfg = (data[4] & 0x60);
    // at lower res, the low bits are undefined, so let's zero them
    if (cfg == 0x00) raw = raw & ~7;  // 9 bit resolution, 93.75 ms
    else if (cfg == 0x20) raw = raw & ~3; // 10 bit res, 187.5 ms
    else if (cfg == 0x40) raw = raw & ~1; // 11 bit res, 375 ms
    //// default is 12 bit resolution, 750 ms conversion time
    celsius = (float)raw / 16.0;
  }
}

void ledOn() {
  digitalWrite(LED_PIN, HIGH);
}

void ledOff() {
 digitalWrite(LED_PIN, LOW);
}

void Log(char* str) {
  #ifdef DEBUG 
    Serial.print(str);
  #endif
  file.print(str);
}

void Logln(char* str) {
  #ifdef DEBUG 
    Serial.println(str);
  #endif
  file.println(str);
}

void LogDec(int d) {
  #ifdef DEBUG 
    Serial.print(d, DEC);
  #endif
  file.print(d, DEC);
}

void LogChar(char c) {
  #ifdef DEBUG 
    Serial.print(c);
  #endif
  file.print(c);
}

void LogDouble(double d) {
  #ifdef DEBUG 
    Serial.print(d, 2);
  #endif
  file.print(d, 2);
}

void Log_P(PGM_P str) {
  #ifdef DEBUG 
    SerialPrint_P(str);
  #endif
  file.write_P(str);
}

void Logln_P(PGM_P str) {
  #ifdef DEBUG 
    SerialPrintln_P(str);  
  #endif  
  file.writeln_P(str);
}

void Error_P(PGM_P str) {
  #ifdef DEBUG   
    Log_P(PSTR("Error: "));
    Logln_P(str);
  #endif
  file.print("Error: ");
  file.print(str);
  if (card.errorCode) {
    #ifdef DEBUG   
      Log_P(PSTR("SD error: "));
      Serial.println(card.errorCode, HEX);
    #endif
    file.println("SD error: ");
    file.println(card.errorCode, HEX);
  }
}

  
// Interrupt service routine for external interrupt on INT0 pin conntected to DS3231 /INT
void INT0_ISR()
{
    //Keep this as short as possible. Possibly avoid using function calls
    detachInterrupt(0); // The interrupt must be detached otherwise the interrupt will keep happening and the ISR will be repeatedly called until the pin changes state.
    interruptTime = DateTime(interruptTime.get() + LOOP_INTERVAL_SEC);  // Decide the time for next interrupt, configure next interrupt.
}

