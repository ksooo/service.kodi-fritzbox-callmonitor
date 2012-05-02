import xbmc, xbmcaddon
import os, time
import socket
import service, asyncore

# Script constants
__addon__       = "Dummy"
__addon_id__    = "service.xbmc-dummy"
__author__      = "N.K."

ip='192.168.178.1'
port = 1012

xbmc.log("DUMMY Started")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip,port))
print 'Connected '
s.setblocking(0)
while (not xbmc.abortRequested):
    try:
        data = s.recv(1024)
        print data
    except socket.error, msg:
        'print no data arrving'
        print msg
    
s.close()   
#    
#client = service.FritzClient('192.168.178.1', 1012)
#asyncore.loop()
#if (xbmc.abortRequested):
#    xbmc.log("DUMMY Aborting...")


xbmc.log("DUMMY Exiting")
