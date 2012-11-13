# Open Source Initiative OSI - The MIT License (MIT):Licensing
#[OSI Approved License]
#The MIT License (MIT)

#Copyright (c) 2011 N.K.
#Copyright (c) 2012 FEP

#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import xbmc, xbmcaddon
import socket
import os
import errno
from pprint import pformat

# own imports
import fritzAddressbook


def errorMsg(aList):
    xbmc.log("Unhandled State: %s" % aList)

#AusgehendeAnrufe
def handleOutgoingCall(aList):
    #datum;CALL;ConnectionID;Nebenstelle;GenutzteNummer;AngerufeneNummer;
    #[192.168.178.1] 03.01.12 22:09:56;CALL;0;0;123456;017500000;SIP1;
    datum, funktion, connectionID, Nebenstelle, GenutzteNummer, AngerufeneNummer, sip,  leer = aList
    xbmc.log(str(aList))
    Notification("Ausgehender Anruf", "zu %s (von %s)" % (AngerufeneNummer, GenutzteNummer))


#EingehendeAnrufe:
def handleIncomingCall(aList):
    #datum;RING;ConnectionID;Anrufer-Nr;Angerufene-Nummer;sip;
    #[192.168.178.1] 03.01.12 21:52:21;RING;0;017100000;012345;SIP2;
    datum, funktion, connectionID, anruferNR, angerufeneNR, sip, leer = aList
    xbmc.log(str(aList))
    anrufer = xbmctelefonbuch.get(aList[3], str(anruferNR))
    PIC = xbmc.translatePath(os.path.join(PicFolder, "%s.png" % aList[3]))
 
    try:
        open(PIC).close()
    except Exception, e:
 	xbmc.log('%s: %s' % (PIC, str(e)))
        PIC = False
 
    Notification('Eingehender Anruf', 'Von %s [%s]' % (anrufer, aList[3]))

#Zustandegekommene Verbindung:
def handleConnected(aList):
    #datum;CONNECT;ConnectionID;Nebenstelle;Nummer;
    datum, funktion, connectionID, nebenstelle, nummer, leer = aList
    xbmc.log(str(aList))
    if __settings__.getSetting( "AC_Pause" )  == 'true':
        xbmc.Player().pause()
    Notification('Verbindung hergestellt', 'Mit %s' % (nummer))

#Ende der Verbindung:
def handleDisconnected(aList):
    #datum;DISCONNECT;ConnectionID;dauerInSekunden;
    #[192.168.178.1] 03.01.12 22:12:56;DISCONNECT;0;0;
    datum, funktion, connectionID, dauer,  leer = aList
    xbmc.log(str(aList))
    Notification('Verbindung beendet', 'Dauer: %i Minuten' % (int(int(dauer)/60)))


def Notification(title, text, duration=False, img=False):
    xbmc.log("%s: %s" % (title, text))
    if not duration:
        duration = __settings__.getSetting( "S_DURATION" )
        duration = int(duration)*1000
    if not img:
        img = xbmc.translatePath(os.path.join( xbmcaddon.Addon().getAddonInfo('path'), "media","default.png"))
    return xbmc.executebuiltin('Notification("%s", "%s", %d, "%s")' % (title, str(text), duration, img))


# Script constants
__addon__       = "XBMC Fritzbox Addon"
__addon_id__    = "service.xbmc-fritzbox"
__author__      = "FEP"
__url__         = "http://code.google.com/p/xbmc-fritzbox"
__version__     = "1"
__settings__    = xbmcaddon.Addon(id='service.xbmc-fritzbox')


Addon = xbmcaddon.Addon(id=__addon_id__)

# Werte der Settings-GUI
ip = __settings__.getSetting( "S_IP" ) 
useFritzAB      = __settings__.getSetting( "AB_Fritzadress" )
fritzAddressURL = __settings__.getSetting( "AB_Adressbookpath")
PicFolder       = __settings__.getSetting( "AB_Pics" )

#Fill Addressbook for lookup
xbmctelefonbuch = {}
if useFritzAB == 'true':
    tmp = fritzAddressbook.Fritzboxtelefonbuch(xbmctelefonbuch, fritzAddressURL)
    xbmctelefonbuch = tmp.getTelefonbuch()


#Get Connection
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.connect((ip, 1012))
except Exception, e:
    Notification('Fritzbox nicht erreichbar', 'Konnte keine Verbindung zur Fritzbox herstellen (%s)' % e);
else:
    xbmc.log('connected to fritzbox callmonitor')
    #s.setblocking(0)
    s.settimeout(0.2)
    while (not xbmc.abortRequested):
        try:
            antwort = s.recv(1024)
            items = antwort.split(';')
            xbmc.log("[%s] %s" % (ip,antwort))
            {
             'CALL': handleOutgoingCall, 
             'RING': handleIncomingCall, 
             'CONNECT': handleConnected, 
             'DISCONNECT': handleDisconnected
            }.get(items[1], errorMsg)(items)
        except IndexError:
            xbmc.log('ERROR: Something is wrong with the message from the fritzbox. unexpected firmware maybe')
        except socket.timeout, e:
            pass
        except socket.error, e:
            xbmc.log('ERROR: Could not connect %s on port 1012. Have you activated the Callmonitor via #96*5*' % ip)
            xbmc.log(pformat(e))
        except Exception, e:
            xbmc.log(pformat(e))
    s.close()
    xbmc.log("XBMC-Fritzbox Addon beendet.")
