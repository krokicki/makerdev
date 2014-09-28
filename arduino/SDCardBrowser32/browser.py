#!/usr/bin/env python
# 
# Basic SD Card Browser for Arduino devices
# Author: Konrad Rokicki
# 

import serial
from serial.tools import list_ports
from cmd import Cmd

BAUD_RATE = 57600
USB_DEVICES = ['tty.usbserial-A1017ICT', 'tty.usbmodem621', 'tty.usbmodem411']

class BrowserPrompt(Cmd):

    def connect(self, device):
        self.ser = serial.Serial(device, BAUD_RATE, timeout=10, writeTimeout=10)

    def openPort(self, args):
        if len(args)>0:
            device = args
            try:
                self.connect(device)
                return
            except:
                print "Could not connect to %s"%device
        else:
            i = 0
            while i<len(USB_DEVICES):
                try:
                    device = "/dev/%s"%USB_DEVICES[i]
                    self.connect(device)
                    return 
                except:
                    i += 1

            print "Could not find Arduino"

    def notConnected(self):
        if not(self.ser):
            print "Not connected to an Arduino! Use 'open' to connect."
            return True
        return False

    def writeCommand(self, command):
        if self.notConnected(): return
        self.ser.write(command+"\n")

    def readUntilPrompt(self):
        if self.notConnected(): return
        pb = ""
        sb = ""
        while True:
            b = self.ser.read()
            if b==0: continue
            if b==">" or sb:
                sb += b
            if len(sb)==4:
                if sb=='> \r\n':
                    return pb[0:-4]
                else:
                    sb = ""

            pb += b    

    def do_ports(self, args):
        for port in list_ports.comports():
            print port[0]

    def do_open(self, args):
        self.openPort(args)
        self.readUntilPrompt()
        print "Connected to port %s" % self.ser.name

    def do_close(self, args):
        self.ser.close()
        print "Port %s closed" % self.ser.name
        self.ser = None

    def do_ls(self, args):
        self.writeCommand("ls")
        print self.readUntilPrompt()
    
    def do_get(self, args):
        filename = args
        self.writeCommand("cat %s"%filename)
        contents = self.readUntilPrompt()
        f = open(filename, "w")
        f.write(contents)
        f.close()
        print "Saved to %s"%filename

    def do_rm(self, args):
        filename = args
        self.writeCommand("rm %s"%filename)
        print self.readUntilPrompt()

    def do_test(self, args):
        filename = args
        self.writeCommand("test %s"%filename)
        print self.readUntilPrompt()

if __name__ == '__main__':
    prompt = BrowserPrompt()
    prompt.prompt = '> '
    prompt.cmdloop('Starting SD Card Browser...')

