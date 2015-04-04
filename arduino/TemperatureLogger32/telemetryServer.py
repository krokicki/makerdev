#!/usr/bin/env python
# 
# Apicultural Telemetry System
# Module: Telemetry Proxy Server
# Author: Konrad Rokicki
# 
# This "proxy" server is meant to be the middle-man between the Arduino logger
# and the data server. It listens for "I'm awake" signals from the logger
# and requests any data it doesn't yet have. All the data is stored locally 
# and proxied to the main data server when possible.
#
# Architecturally, the system looks like this:
#
# [data server] <--- REST ---> [proxy server] <--- Serial ---> [logger]
#
# Each site maintains its own copy of the data in case a connection cannot be made 
# and the data needs to be resent at a later time.
#
# The "I'm awake" signal is a command prompt consisting of 4 characters: "> \r\n"
#
# Upon hearing this, the proxy responds with a PULL command:
# "PULL 2014/10/1,0:2:2" will request all data newer than the given date/time.
#
# The logger will print all the data lines requested, followed by another prompt. 
# 

import serial
import signal
import sys
from serial.tools import list_ports
from cmd import Cmd
from os import listdir
from os.path import isfile, join

BAUD_RATE = 57600
USB_DEVICES = ['tty.usbserial-A1017ICT', 'tty.usbmodem621', 'tty.usbmodem411']

class TelemetryServer():

    def __init__(self):
        path = '.'
        filenames = sorted([ f for f in listdir(path) \
            if isfile(join(path,f)) and f.lower().endswith('.log')])   
        lastFile = open(filenames[-1], "r")
        for line in lastFile:
            fields = line.split(',')
            if len(fields)>1:
                self.lastDateTime = '%s,%s'%(fields[0],fields[1])
            else:
                print line
        if self.lastDateTime:
            print "Last date/time received was %s"%self.lastDateTime
        else:
            print "No records found! Starting fresh."
            self.lastDateTime = "1970/1/1,0:0:0"

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

            for port in list_ports.comports():
                device = port[0]
                if not("Bluetooth" in device):
                    self.connect(device)
                    return

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
            if b==0: return None
            if b==">" or sb:
                sb += b
            if len(sb)==4:
                if sb=='> \r\n':
                    return pb[0:-4]
                else:
                    sb = ""
            pb += b

    def begin(self):
        self.openPort(sys.argv[1:])
        print "Connected to port %s" % self.ser.name

    def end(self):
        self.ser.close()
        print "Port %s closed" % self.ser.name
        self.ser = None

    def pullDate(self):

        self.writeCommand("get %s"%self.lastDateTime)

        filename = "telemetry.log"

        contents = self.readUntilPrompt()
        f = open(filename, "a")
        f.write(contents)
        f.close()
        print "Appended to %s"%filename

    def loop(self):
        while True:
            if self.readUntilPrompt():
                self.pullData()
            time.sleep(2)



if __name__ == '__main__':
    server = TelemetryServer()
    server.begin()
    def signal_handler(signal, frame):
        print('You pressed Ctrl+C!')
        server.end()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    print('Press Ctrl+C to exit')
    server.loop()


