# Open Source Initiative OSI - The MIT License (MIT):Licensing
#[OSI Approved License]
#The MIT License (MIT)

#Copyright (c) 2011 N.K.

#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# ################################################################################
# author: nk
# version: 0.9.3.1
# ################################################################################

import xbmc, xbmcaddon
import socket
import os


# [1]
#Default Fehler
def errorMsg(aList):
    text = "Unhandled State"
    xbmc.log(text)

#AusgehendeAnrufe
def handleOutgoingCall(aList):
    #datum;CALL;ConnectionID;Nebenstelle;GenutzteNummer;AngerufeneNummer;
    #[192.168.178.1] 03.01.12 22:09:56;CALL;0;0;123456;017500000;SIP1;
    datum, funktion, connectionID, Nebenstelle, GenutzteNummer, AngerufeneNummer, sip,  leer = aList
    logtext = ('Ausgehender Anruf an %s von Nr: %s, am %s' % (AngerufeneNummer, GenutzteNummer, datum))
    heading = "Ausgehender Anruf"
    text = "Angerufene Nr. %s von Apparat Nr: %s" % (AngerufeneNummer, GenutzteNummer)
    xbmc.log(logtext)
    xbmc.executebuiltin("Notification("+heading+","+text+","+duration+","+DEFAULT_IMG+")")


#EingehendeAnrufe:
def handleIncomingCall(aList):
    #datum;RING;ConnectionID;Anrufer-Nr;Angerufene-Nummer;sip;
    #[192.168.178.1] 03.01.12 21:52:21;RING;0;017100000;012345;SIP2;
    datum, funktion, connectionID, anruferNR, angerufeneNR, sip, leer = aList
    logtext = ('Eingehender Anruf von %s auf Apparat %s' % (aList[3], aList[4]))
    heading = 'Eingehender Anruf'
    text = 'von %s auf Apparat %s' % (aList[3], aList[4])
    xbmc.log(logtext)
    xbmc.executebuiltin("Notification("+heading+","+text+","+duration+","+DEFAULT_IMG+")")

#Zustandegekommene Verbindung:
def handleConnected(aList):
    #datum;CONNECT;ConnectionID;Nebenstelle;Nummer;
    datum, funktion, connectionID, nebenstelle, nummer, leer = aList
    logtext = ('Verbunden mit %s' % (nummer))
    #print text
    heading = 'Verbindung hergestellt'
    text = 'mit %s' % (nummer)
    xbmc.log(logtext)
    xbmc.executebuiltin("Notification("+heading+","+text+","+duration+","+DEFAULT_IMG+")")

#Ende der Verbindung:
def handleDisconnected(aList):
    #datum;DISCONNECT;ConnectionID;dauerInSekunden;
    #[192.168.178.1] 03.01.12 22:12:56;DISCONNECT;0;0;
    datum, funktion, connectionID, dauer,  leer = aList
    text = ('Anrufdauer: %s Minuten' % (int(int(dauer)/60)))
    #print text
    xbmc.log(text)
    xbmc.executebuiltin("Notification(XBMC-Fritzbox,"+text+","+duration+","+DEFAULT_IMG+")")


# Script constants
__addon__       = "XBMC Fritzbox Addon"
__addon_id__    = "service.xbmc-fritzbox"
__author__      = "N.K."
__url__         = "http://code.google.com/p/xbmc-fritzbox"
__version__     = "0.9.3.1"
__settings__ = xbmcaddon.Addon(id='service.xbmc-fritzbox')

xbmc.log("xbmc-fritzbox ShowCallerInfo-Service starting...")
DEFAULT_IMG = xbmc.translatePath(os.path.join( "special://home/", "addons", "service.xbmc-fritzbox", "media","default.png"))
Addon = xbmcaddon.Addon(id='service.xbmc-fritzbox')
# Werte der Settings-GUI
ip = __settings__.getSetting( "S_IP" ) # return FritzIP setting value 
dur = __settings__.getSetting( "S_DURATION" ) # return Anzeigedauer
durdict = {'1': '1000','2': '2000' ,'3':'3000','4':'4000','5':'5000','8':'8000','10':'10000','15':'15000','0':'0'}
duration = durdict.get(dur) # Unit conversion Seconds_2_Milliseconds, NotificationDialog wants Milliseconds
debuggen = __settings__.getSetting("S_DEBUG")

# -------------- Addressbook-Lookup-Settings ---------
#TODO:
#AB_Fritzadress
#AB_Adressbookpath
#AB_Textfile
#AB_CSVpath
#AB_iPhone
#AB_iPhoneAddressbook
#AB_iPhoneAddressbookImages
# -------------- Action Settings -----
#TODO:
parameterstring = "Fritzbox: Ip Adresse definiert als %s" % ( ip)
xbmc.log(parameterstring)
fncDict = {'CALL': handleOutgoingCall, 'RING': handleIncomingCall, 'CONNECT': handleConnected, 'DISCONNECT': handleDisconnected}
#run the program
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
s.connect((ip, 1012))
xbmc.log('connected to fritzbox callmonitor')
s.setblocking(0)
while (not xbmc.abortRequested):
    try:
        antwort = s.recv(1024) 
        log= "[%s] %s" % (ip,antwort)
        #xbmc.log(log)
        items = antwort.split(';')
        fncDict.get(items[1], errorMsg)(items)
    except IndexError:
        text = 'ERROR: Something is wrong with the message from the fritzbox'
        #print text
        xbmc.log(text)
    except socket.error, msg:
        text = 'ERROR: Could not connect fritz.box on port 1012'
        xbmc.log(text)

s.close()

xbmc.log("XBMC-Fritzbox Addon beendet.")
