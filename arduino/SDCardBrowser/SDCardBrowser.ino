/*
 * This sketch allows you to use the serial monitor to list files on an SD card and print them.
 */
#include <Fat16.h>
#include <Fat16util.h> // use functions to print strings from flash memory

SdCard card;
Fat16 file;

// store error strings in flash to save RAM
#define error(s) error_P(PSTR(s))

void error_P(const char*  str) {
  PgmPrint("error: ");
  SerialPrintln_P(str);
  if (card.errorCode) {
    PgmPrint("SD error: ");
    Serial.println(card.errorCode, HEX);
  }
  while(1);
}

void setup(void) {
  Serial.begin(57600);
  
  // initialize the SD card
  if (!card.init()) error("card.init");
  
  // initialize a FAT16 volume
  if (!Fat16::init(&card)) error("Fat16::init"); 
}

void loop(void) {

  Serial.println("Enter index of file to print:");
      
  dir_t d;
  int fileIndex = 0;
  for (uint16_t index = 0; file.readDir(&d, &index, DIR_ATT_VOLUME_ID); index++) {
    // print file name with possible blank fill
    Serial.print("  ");
    Serial.print(fileIndex);
    Serial.print(" : ");
    file.printDirName(d, LS_DATE | LS_SIZE);
    Serial.println();
    fileIndex++;
  }

  while (!Serial.available());
  int inputIndex = Serial.parseInt();
  Serial.print("Printing file with index ");
  Serial.println(inputIndex);
  
  String filenameStr = "";
  fileIndex = 0;
  for (uint16_t index = 0; file.readDir(&d, &index, DIR_ATT_VOLUME_ID); index++) {
    if (fileIndex==inputIndex) {
      uint8_t w = 0;  
      for (uint8_t i = 0; i < 11; i++) {
        if (d.name[i] == ' ') continue;
        if (i == 8) {
          filenameStr += ".";
          w++;
        }
        filenameStr += (char)d.name[i];
        w++;
      }
      if (DIR_IS_SUBDIR(&d)) {
        filenameStr += "/";
        w++;
      }
    }
    fileIndex++;
  }
  
  char filename[filenameStr.length()+1];
  filenameStr.toCharArray(filename, sizeof(filename));
  
  Serial.print("Printing file with name ");
  Serial.println(filenameStr);
  
  // open a file
  if (!file.open(filename, O_READ)) {
    error("file.open");
  }
  
  // copy file to serial port
  int16_t n;
  uint8_t buf[7]; 
  while ((n = file.read(buf, sizeof(buf))) > 0) {
    for (uint8_t i = 0; i < n; i++) Serial.write(buf[i]);
  }
  PgmPrintln("\n");
}
