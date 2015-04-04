// Data Logger (FAT32 version)
// Improvements upon the default Stalker logger example:
// - Using flash memory for all strings
// - Battery status logging
// - Seeeduino onboard temperature logging
// - OneWire DS18B20 external temperature logging
// - Uses SdFat library for Fat32 logging
// - Optional wireless telemetry
//
// For Seeduino Stalker use: Arduino Pro or Pro Mini (3.3V, Mhz) w/ ATmega328

//#define SLEEP
#define DEBUG

#ifdef SLEEP
#include <avr/sleep.h>
#include <avr/power.h>
#endif

#include <Wire.h>
#include <DS3231.h>
#include <SdFat.h>
#include <SdFatUtil.h>
#include <Battery.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <EEPROM.h>

#define LINE_BUFFER_SIZE 200
#define MAX_LINES_PER_SESSION 10
#define BAUD_RATE 57600
#define BUFFER_SIZE 80

#define TF_POWER_PIN 4
#define BEE_POWER_PIN 5
#define ONE_WIRE_BUS 6
#define LED_PIN 9
#define CHIP_SELECT 10

//#define LOOP_INTERVAL_SEC 300 // 5 minutes
#define LOOP_INTERVAL_SEC 30 // 5 Seconds
#define SECS_SINCE_2000 946684800 // Seconds since 1/1/2000, to convert DS3231 time to UNIX epoch time

#define PgmLog(x) Log_P(PSTR(x))
#define PgmLogChar(x) LogChar(x)
#define PgmLogDec(x) LogDec(x)
#define PgmLogLong(x) LogLong(x)
#define PgmLogDouble(x) LogDouble(x)
#define PgmLogln(x) Logln_P(PSTR(x))
#define PgmError(x) Error_P(PSTR(x))

#ifdef SLEEP
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
#endif

DS3231 RTC; 
DateTime interruptTime;
SdFat sd;
SdFile file;
Battery battery;
OneWire ds(ONE_WIRE_BUS);
DallasTemperature sensors(&ds);

#define NUM_PROBES 20
char* idStrs[] = {
"2881b859050000cc",
"28f7245a050000f8",
"28a3065a05000071",
"28c05766050000e9",
"28e8e259050000b1",
"280e0a5a05000046",
"28b7db59050000cc",
"28f6d5590500002c",
// 9-12 were trashed
//"2826cc5905000067", 
//"28373c5a05000025",
//"285e27d10400009a",
//"289f0ad0040000a9",
"28a12cd1040000bc",
"287f48d0040000ea",
"28913fd0040000ec",
"28bdadd004000013",
"28df11d0040000d0",
"28bd4cd004000004",
"28a65dd004000016",
"283081d00400006a",
"28ff361b6b0400a3",
"28ff6b56541400ca",
"28ff97565414004d",
"28ffd755770400b0"
};

byte ids[NUM_PROBES][8];

void setup() {

    // Initialize pins for controlling power to various components 
    pinMode(TF_POWER_PIN, OUTPUT);  
    pinMode(BEE_POWER_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);  
    
    // Initialize libaries
    Wire.begin();
    RTC.begin();
    sensors.begin();
      
    // Power on components
    digitalWrite(TF_POWER_PIN, HIGH);
    digitalWrite(BEE_POWER_PIN, HIGH);
    digitalWrite(LED_PIN, HIGH);
    
    // Read time from RTC
    DateTime now = RTC.now();
    
    Serial.begin(BAUD_RATE);
    Serial.println("SETUP");
    
    // Wait for components to initialize
    delay(1000); 
    
    // Log the Begin event
    long ts = now.get()+SECS_SINCE_2000;
    PgmLogLong(ts);
    PgmLog(",");    
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

    digitalWrite(LED_PIN, LOW);
    
    #ifdef SLEEP
      Serial.println("SLEEP");
      // Initialize INT0 pin for accepting interrupts 
      PORTD |= 0x04; // set pin 2 to HIGH 
      DDRD &=~ 0x04; // set pin 2 to OUTPUT
      attachInterrupt(0, INT0_ISR, LOW); // Only LOW level interrupt can wake up from PWR_DOWN
      set_sleep_mode(SLEEP_MODE_PWR_DOWN);
      
      // Enable Interrupt 
      interruptTime = DateTime(now.get() + LOOP_INTERVAL_SEC);
    #endif
}

void loop() {
      
    Serial.println("LOOP");
      
    // Parse device addresses
    for(int i=0; i<NUM_PROBES; i++) {
      for(int j=0; j<8; j++) {
          char strPart[3];
          strPart[0] = idStrs[i][j*2];
          strPart[1] = idStrs[i][j*2+1];
          strPart[2] = NULL;
          long unsigned int id = strtoul(strPart, NULL, 16);
          ids[i][j] = id;
      }
    }
    
    #ifdef SLEEP
      // Turn on everything back on
      digitalWrite(TF_POWER_PIN, HIGH);
      #ifdef TELEMETRY
        digitalWrite(BEE_POWER_PIN, HIGH); 
      #endif
    
      // Wait for SD card to power up
      delay(1000);
        
      // Initialize the SD card
      if (!sd.begin(CHIP_SELECT, SPI_FULL_SPEED)) {
        PgmError("sd.begin");
        sd.initErrorHalt();
      }
    #endif
    
    digitalWrite(LED_PIN, HIGH);
    
    // Read time from RTC
    DateTime now = RTC.now();
    
    char filename[11];
    setLogFilename(now.year(), now.month(), filename);
    
    // Initialize the SD card
    if (!sd.begin(CHIP_SELECT, SPI_FULL_SPEED)) {
      PgmError("sd.begin");
      sd.initErrorHalt();
    }
    
    if (!file.open(filename, O_RDWR | O_CREAT | O_AT_END)) {
      PgmError("Error opening file");
      sd.errorHalt("Opening file for write failed");
    }
    
    // Read one-wire bus
    sensors.requestTemperatures();
      
    // Read battery status
    battery.update();
    float voltage = battery.getVoltage();
    int percentage = battery.getPercentage();
    char* chargeStatus = battery.getChStatus();
    
    // Read built-in temperature
    RTC.convertTemperature();
    float internalTemp = RTC.getTemperature();

    long ts = now.get()+SECS_SINCE_2000;
    PgmLogLong(ts);
    PgmLog(",");    
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
    
    for(int i=0; i<NUM_PROBES; i++) {
      PgmLog(",");
      PgmLogDouble(sensors.getTempC(ids[i]));   
    }
    
    Logln("");

    #ifdef SLEEP  
      Serial.println("Closing file for sleep");
      if (!file.close()) {
        PgmError("error closing file");
      }    
      Serial.println("Powering off SD card");
      // Turn off SD card to conserve power
      digitalWrite(TF_POWER_PIN, LOW);
    #else
      Serial.println("Closing file");
      if (!file.close()) {
        PgmError("error closing file");
      }    
    #endif
  
    #ifdef SLEEP
      // Wait a little longer to make sure we have a telemetry connection     
      delay(1000);
    #endif
      
    // Send a command prompt and wait for server to request data
    Serial.println("> ");

//    static char buffer[BUFFER_SIZE];
//    if (readline(buffer, BUFFER_SIZE) > 0) {
//    
//      char *command, *args, *tok;
//      command = strtok_r(buffer," ",&tok);
//      args = strtok_r(NULL," ",&tok);  
//      
//      if (strcmp(command,"pull")==0) {
//        int timestamp = atoi(args);
//        DateTime ts = DateTime(timestamp);
//            
//        char *filename = getLogFilename(ts.year(), ts.month());  
//        
//        if (!file.open(filename, O_READ)) {
//          Serial.println("Error opening file");
//          sd.errorPrint();
//        }
//        else {
//          // copy file to serial port
//          boolean newline = true;
//          uint8_t tlinenum = -1;
//          char* tsbuf = new char[11];
//          tsbuf[10] = 0; // terminate string with null
//          
//          int lineTimestamp = 0;
//          int16_t n;
//          uint8_t buf[8]; 
//          char linebuf[LINE_BUFFER_SIZE]; 
//          uint8_t linepos = 0; 
//          while ((n = file.read(buf, sizeof(buf))) > 0) {
//            
//            // Copy the read buffer into the line buffer
//            for (uint8_t i = 0; i < n; i++) {
//              char b = buf[i];
//              linebuf[linepos++] = b;
//              
//              // Wait for EOL
//              if (b=='\n') {
//                if (tlinenum>=0) {
//                  // We need to transmit this line
//                  for (uint8_t j = 0; j < LINE_BUFFER_SIZE; j++) {
//                    Serial.write(linebuf[j]);
//                    if (linebuf[j]=='\n') break;
//                  }
//                  tlinenum++;
//                }
//                // Reset line buffer
//                linepos = 0;
//                // Look for next timestamp
//                newline = true;
//              }
//              
//              // Check for timestamp at the beginning of each line
//              if (newline && b==',') {
//                strlcpy(linebuf, tsbuf, 10);
//                lineTimestamp = atoi(tsbuf);
//                // If we haven't started transmitting, check if we should begin
//                if (tlinenum<0 && lineTimestamp>=timestamp) {
//                  tlinenum = 0;
//                }
//                // Got timestamp, stop looking for it on this line
//                newline = false;
//              }
//            }
//            
//            // Have we done enough?
//            if (tlinenum>MAX_LINES_PER_SESSION) break;
//          }  
//          file.close();
//        }
//      }
//      else {
//        Serial.println("Unknown command"); 
//      }
//      
//    }
    
    // Turn off LED    
    digitalWrite(LED_PIN, LOW);
      
    #ifdef SLEEP  
      
      // Turn off radio
      digitalWrite(BEE_POWER_PIN, LOW); 
      
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
  
    #else
      delay(5000);   
    #endif
} 


void setLogFilename(int y, int m, char* filename) {
  char yearChar[5];
  char monthChar[3];
  itoa(y,yearChar,10);
  itoa(m,monthChar,10);
  strlcpy(filename, yearChar, 5);
  strlcpy(filename+4, monthChar, 3);
  strlcpy(filename+6, ".LOG", 5);
  filename[10] = NULL;
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

void LogLong(long d) {
  #ifdef DEBUG 
    Serial.print(d, DEC);
  #endif
  file.print(d, DEC);
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
}

int readline(char *buffer, int len)
{
  int pos = 0;
  while (pos < len-1) {
    int i=0;
    while (!Serial.available()) {
      delay(10);  
      if (i++ >200) return 0;
    }
    byte b = Serial.read();
    switch (b) {
      case '\r': // Ignore CR
        break;
      case '\n': // Return on newline
        return pos;
      default:
        buffer[pos++] = b;
        buffer[pos] = 0;
    }
  }
  return pos;
}
  
// Interrupt service routine for external interrupt on INT0 pin conntected to DS3231 /INT
void INT0_ISR()
{
    //Keep this as short as possible. Possibly avoid using function calls
    detachInterrupt(0); // The interrupt must be detached otherwise the interrupt will keep happening and the ISR will be repeatedly called until the pin changes state.
    interruptTime = DateTime(interruptTime.get() + LOOP_INTERVAL_SEC);  // Decide the time for next interrupt, configure next interrupt.
}

