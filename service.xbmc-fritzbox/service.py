# Open Source Initiative OSI - The MIT License (MIT):Licensing
#[OSI Approved License]
#The MIT License (MIT)

#Copyright (c) 2011 N.K.

#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# ################################################################################
# author: nk
# version: 0.9.4
# ################################################################################

import xbmc, xbmcaddon
import socket
import os

class FritzCaller():

    def __init__(self,s=None):
        # Const
        self.__addon__       = "XBMC Fritzbox Addon"
        self.__addonid__     = "service.xbmc-fritzbox"
        self.__author__      = "N.K."
        self.__url__         = "http://code.google.com/p/xbmc-fritzbox/"
        self.__version__     = "0.9.4"
        
        # ------------------ XBMC-Settings --------------------------
        self.__settings__    = xbmcaddon.Addon(self.__addonid__)
        # Generic
        self.__datadir__     = self.__settings__.getAddonInfo('profile')
        self.__addondir__    = self.__settings__.getAddonInfo('path')
        self.__defaultIMG__  = xbmc.translatePath(os.path.join(self.__addondir__,"media","default.png"))
        # less secure
        #self.__defaultIMG__  = xbmc.translatePath(os.path.join( "special://home/", "addons", "service.xbmc-fritzbox", "media","default.png"))
        # GUI Settings
        # -------------- Essential Main Settings -------
        self.__FritzIP__     = self.__settings__.getSetting( "S_IP" ) # return Fritzbox IP setting value 
        self.__Displaydur__  = self.__settings__.getSetting( "S_DURATION" ) # Unit conversion Seconds_2_Milliseconds, NotificationDialog wants Milliseconds  
        self.__Debug__       = self.__settings__.getSetting("S_DEBUG")
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
        
        #--------------- addon initlisation -----------
        #Function Dictionary
        self.__fncDict__ = {'CALL': self.handleOutgoingCall, 'RING': self.handleIncomingCall, 'CONNECT': self.handleConnected, 'DISCONNECT': self.handleDisconnected}
        # --------------- Sockets for Fritzbox --------------
        if s is None:
            self.__s__ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.__s__ = s
        
        
        
    def logAllVariables(self):
        
        self.log("Fritzbox IP-Address is: %s" % ( self.__FritzIP__))
        self.log("DisplayDuration is: %s" % ( self.__Displaydur__))
        self.log("ProfileDatadir is: %s" % (xbmc.translatePath(self.__datadir__)))
        self.log("AddonDir is: %s" % (self.__addondir__))
        self.log("DefaultImage is: %s" % (self.__defaultIMG__))
        
    def stopService(self):             
        self.__s__.close()
        self.log("Connection to Socket closed")
        self.log("Stopping service")   

        
    def startService(self):
        
        if self.__Debug__:
            self.logAllVariables()
        
        try:
            self.__s__.connect((self.__FritzIP__, 1012))
            self.log('connected to fritzbox callmonitor successful')
            antwort = self.__s__.recv(1024)
#            if not antwort: 
#                break
            log= "[%s] %s" % (self.__FritzIP__,antwort)
            self.log(log)
            items = antwort.split(';')
            self.__fncDict__.get(items[1], self.errorMsg)(items)

        
        except IndexError:
            text = 'ERROR: Something is wrong with the message from the fritzbox. Unexpected firmware maybe'
            #print text
            self.log(text)
            self.__s__.close()
        except socket.error, msg:
            text = 'ERROR: Could not connect fritz.box on port 1012. Have you activated the Callmonitor via #96*5*'
            xbmc.log(text)
            self.__s__.close()
        finally:
            self.__s__.close()
        
    # [1]
    #Default Fehler
    def errorMsg(self,aList):
        text = "Unhandled State"
        self.log(text)
    # [2]
    #AusgehendeAnrufe
    def handleOutgoingCall(self,aList):
        #datum;CALL;ConnectionID;Nebenstelle;GenutzteNummer;AngerufeneNummer;
        #[192.168.178.1] 03.01.12 22:09:56;CALL;0;0;123456;017500000;SIP1;
        datum, funktion, connectionID, Nebenstelle, GenutzteNummer, AngerufeneNummer, sip,  leer = aList
        logtext = ('Ausgehender Anruf an %s von Nr: %s, am %s' % (AngerufeneNummer, GenutzteNummer, datum))
        heading = "Ausgehender Anruf"
        text = "Angerufene Nr. %s von Apparat Nr: %s" % (AngerufeneNummer, GenutzteNummer)
        self.log(logtext)
        xbmc.executebuiltin("Notification("+heading+","+text+","+self.__Displaydur__+","+self.__defaultIMG__+")")
    

    #EingehendeAnrufe:
    def handleIncomingCall(self,aList):
        #datum;RING;ConnectionID;Anrufer-Nr;Angerufene-Nummer;sip;
        #[192.168.178.1] 03.01.12 21:52:21;RING;0;017100000;012345;SIP2;
        datum, funktion, connectionID, anruferNR, angerufeneNR, sip, leer = aList
        logtext = ('Eingehender Anruf von %s auf Apparat %s' % (aList[3], aList[4]))
        heading = 'Eingehender Anruf'
        text = 'von %s auf Apparat %s' % (aList[3], aList[4])
        self.log(logtext)
        xbmc.executebuiltin("Notification("+heading+","+text+","+self.__Displaydur__+","+self.__defaultIMG__+")")
    
    #Zustandegekommene Verbindung:
    def handleConnected(self,aList):
        #datum;CONNECT;ConnectionID;Nebenstelle;Nummer;
        datum, funktion, connectionID, nebenstelle, nummer, leer = aList
        logtext = ('Verbunden mit %s' % (nummer))
        #print text
        self.log(logtext)
        xbmc.executebuiltin("Notification(XBMC-Fritzbox,"+text+","+self.__Displaydur__+","+self.__defaultIMG__+")")
    
    #Ende der Verbindung:
    def handleDisconnected(self,aList):
        #datum;DISCONNECT;ConnectionID;dauerInSekunden;
        #[192.168.178.1] 03.01.12 22:12:56;DISCONNECT;0;0;
        datum, funktion, connectionID, dauer,  leer = aList
        text = ('Anrufdauer: %s Minuten' % (int(dauer/60)))
        #print text
        self.log(text)
        xbmc.executebuiltin("Notification(XBMC-Fritzbox,"+text+","+self.__Displaydur__+","+self.__defaultIMG__+")")
    
    
    
    def log(self,message):
        xbmc.log('service.xbmc-fritzbox: ' + message)




## [1]
##Default Fehler
#def errorMsg(aList):
#    text = "Unhandled State"
#    xbmc.log(text)
#
##AusgehendeAnrufe
#def handleOutgoingCall(aList):
#    #datum;CALL;ConnectionID;Nebenstelle;GenutzteNummer;AngerufeneNummer;
#    #[192.168.178.1] 03.01.12 22:09:56;CALL;0;0;123456;017500000;SIP1;
#    datum, funktion, connectionID, Nebenstelle, GenutzteNummer, AngerufeneNummer, sip,  leer = aList
#    text = ('Ausgehender Anruf an %s von Nr: %s, am %s' % (AngerufeneNummer, GenutzteNummer, datum))
#    #print text
#    xbmc.log(text)
#    xbmc.executebuiltin("Notification(XBMC-Fritzbox,"+text+","+duration+","+DEFAULT_IMG+")")
#
#
##EingehendeAnrufe:
#def handleIncomingCall(aList):
#    #datum;RING;ConnectionID;Anrufer-Nr;Angerufene-Nummer;sip;
#    #[192.168.178.1] 03.01.12 21:52:21;RING;0;017100000;012345;SIP2;
#    datum, funktion, connectionID, anruferNR, angerufeneNR, sip, leer = aList
#    text = ('Eingehender Anruf von %s auf Apparat %s' % (aList[3], aList[4]))
#    #print text
#    xbmc.log(text)
#    xbmc.executebuiltin("Notification(XBMC-Fritzbox,"+text+","+duration+","+DEFAULT_IMG+")")
#
##Zustandegekommene Verbindung:
#def handleConnected(aList):
#    #datum;CONNECT;ConnectionID;Nebenstelle;Nummer;
#    datum, funktion, connectionID, nebenstelle, nummer, leer = aList
#    text = ('Verbunden mit %s' % (nummer))
#    #print text
#    xbmc.log(text)
#    xbmc.executebuiltin("Notification(XBMC-Fritzbox,"+text+","+duration+","+DEFAULT_IMG+")")
#
##Ende der Verbindung:
#def handleDisconnected(aList):
#    #datum;DISCONNECT;ConnectionID;dauerInSekunden;
#    #[192.168.178.1] 03.01.12 22:12:56;DISCONNECT;0;0;
#    datum, funktion, connectionID, dauer,  leer = aList
#    text = ('Anrufdauer: %s Minuten' % (int(dauer/60)))
#    #print text
#    xbmc.log(text)
#    xbmc.executebuiltin("Notification(XBMC-Fritzbox,"+text+",5000,"+DEFAULT_IMG+")")
#
#
#
#
#DEFAULT_IMG = xbmc.translatePath(os.path.join( "special://home/", "addons", "service.xbmc-fritzbox", "media","default.png"))
#Addon = xbmcaddon.Addon(id='service.xbmc-fritzbox')
## Werte der Settings-GUI
#ip = __settings__.getSetting( "S_IP" ) # return FritzIP setting value 
#dur = __settings__.getSetting( "S_DURATION" ) # return Anzeigedauer
#duration = dur * 1000 # Unit conversion Seconds_2_Milliseconds, NotificationDialog wants Milliseconds
#
#parameterstring = "Fritzbox: Ip Adresse definiert als %s" % ( ip)
#xbmc.log(parameterstring)
#fncDict = {'CALL': handleOutgoingCall, 'RING': handleIncomingCall, 'CONNECT': handleConnected, 'DISCONNECT': handleDisconnected}
##run the program
#while(not xbmc.abortRequested):
#    try:
#        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
#        s.connect((ip, 1012))
#        while True:
#            #xbmc.log('connected to fritzbox callmonitor')
#            antwort = s.recv(1024) 
#            log= "[%s] %s" % (ip,antwort)
#            #xbmc.log(log)
#            items = antwort.split(';')
#            fncDict.get(items[1], errorMsg)(items)
#        s.close()
#        if (xbmc.abortRequested):
#            xbmc.log("XBMC-fritzbox Aborting...")
#            s.close()
#            break
#    except IndexError:
#        text = 'ERROR: Something is wrong with the message from the fritzbox'
#        #print text
#        xbmc.log(text)
#    except socket.error, msg:
#        text = 'ERROR: Could not connect fritz.box on port 1012'
#        xbmc.log(text)
#    finally:
#        s.close()
#        
#    


