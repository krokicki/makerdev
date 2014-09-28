/*
 * This sketch allows you to use the serial monitor to list files on an SD card and print them.
 */
#include <SdFat.h>
#include <SdFatUtil.h>

#define BAUD_RATE 57600
#define CHIP_SELECT 10
#define BUFFER_SIZE 80

SdFat sd;
SdFile file;

void setup(void) {
  
  Serial.begin(BAUD_RATE);

  if (!sd.begin(CHIP_SELECT, SPI_FULL_SPEED)) {
    Serial.println("Error initializing SD card");
    sd.initErrorHalt();
  }
}

void loop(void) {
  
  Serial.println("> ");

  static char buffer[BUFFER_SIZE];
  if (readline(buffer, BUFFER_SIZE) < 1) {
    return;
  }
  
  char *command, *args, *tok;
  command = strtok_r(buffer," ",&tok);
  args = strtok_r(NULL," ",&tok);  
  
  if (strcmp(command,"ls")==0) {
    sd.ls("/", LS_R | LS_DATE | LS_SIZE); 
  }
  else if (strcmp(command,"cat")==0) {
    char *filename = args;
    // open a file
    if (!file.open(args, O_READ)) {
      Serial.println("Error opening file");
      sd.errorPrint();  
    }
    else {
      // copy file to serial port
      int16_t n;
      uint8_t buf[7]; 
      while ((n = file.read(buf, sizeof(buf))) > 0) {
        for (uint8_t i = 0; i < n; i++) Serial.write(buf[i]);
      }  
      file.close();
    }
  }
  else if (strcmp(command,"rm")==0) {
    char *filename = args;
    if (!sd.remove(filename)) {
      Serial.println("Error deleting file");
      sd.errorPrint();
    }
    else {
      Serial.println("File removed");
    }
  }
  else if (strcmp(command,"test")==0) {
    char *filename = args;
    if (!file.open(filename, O_RDWR | O_CREAT | O_TRUNC)) {
      Serial.println("Error writing test file");
      sd.errorPrint();
    }
    else {
      file.println("TEST");
      file.close();
      Serial.println("Test file written");
    }
  }
  else {
    Serial.println("Unknown command"); 
  }
}

int readline(char *buffer, int len)
{
  int pos = 0;
  while (pos < len-1) {
    while (!Serial.available()) {} // wait for next character
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
