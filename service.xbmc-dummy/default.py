import xbmc, xbmcaddon
import os, time
import socket
import threading

# Script constants
__addon__       = "Dummy"
__addon_id__    = "service.xbmc-dummy"
__author__      = "N.K."


xbmc.log("DUMMY Started")
 
while 1:
    print "DUMMY Abort Requested: "+str(xbmc.abortRequested)
    if (xbmc.abortRequested):
        xbmc.log("DUMMY Aborting...")
        break
    time.sleep(1)
 

xbmc.log("DUMMY Exiting")
