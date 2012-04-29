import xbmc, xbmcaddon
import os, time
import socket
import service, asyncore

# Script constants
__addon__       = "Dummy"
__addon_id__    = "service.xbmc-dummy"
__author__      = "N.K."


xbmc.log("DUMMY Started")
 
while 1:
    print "DUMMY Abort Requested: "+str(xbmc.abortRequested)
    client = service.FritzClient('192.168.178.1', 1012)
    asyncore.loop()
    if (xbmc.abortRequested):
        xbmc.log("DUMMY Aborting...")
        client.handle_close()
        break
    time.sleep(1)
 

xbmc.log("DUMMY Exiting")
