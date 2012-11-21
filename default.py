from pprint import pformat
import xbmc, xbmcaddon
import socket
import os
from lib.PytzBox import PytzBox


# Script constants
__addon__       = xbmcaddon.Addon()
__addon_id__    = "service.xbmc-fritzbox"
__version__     = "1"



class FritzCallmonitor():

    __pytzbox = None
    __fb_phonebook = None

    def error(*args, **kwargs):
        xbmc.log("ERROR: %s %s" % (args, kwargs))

    def getNameByNumber(self, request_number):

        if __addon__.getSetting( "AB_Fritzadress" ) == 'true':

            if self.__pytzbox is None:

                password = False
                if __addon__.getSetting( "AB_FritzboxPassword" ) and len(str(__addon__.getSetting( "AB_FritzboxPassword" ))) > 0:
                    password = __addon__.getSetting( "AB_FritzboxPassword" )

                self.__pytzbox = PytzBox.PytzBox(password=password, host=__addon__.getSetting( "S_IP" ))

                if password:
                    self.__pytzbox.login()

            if self.__fb_phonebook is None:
                self.__fb_phonebook = self.__pytzbox.getPhonebook()

            if isinstance(self.__fb_phonebook, dict):
                for entry in self.__fb_phonebook:
                    if 'numbers' in self.__fb_phonebook[entry]:
                        for number in self.__fb_phonebook[entry]['numbers']:
                            if number.endswith(request_number):
                                return entry

        return False



    def handleOutgoingCall(self, aList):
        datum, funktion, connectionID, Nebenstelle, GenutzteNummer, AngerufeneNummer, sip,  leer = aList
        xbmc.log(str(aList))
        name = self.getNameByNumber(AngerufeneNummer) or 'Unbekannt'
        self.Notification("Ausgehender Anruf", "zu %s [%s] (von %s)" % (name, AngerufeneNummer, GenutzteNummer))

    def handleIncomingCall(self, aList):
        xbmc.log(str(aList))
        number = aList[3]
        name = self.getNameByNumber(number) or 'Unbekannt'
        self.Notification('Eingehender Anruf', 'Von %s [%s]' % (name, number))

    def handleConnected(self, aList):
        datum, funktion, connectionID, nebenstelle, nummer, leer = aList
        xbmc.log(str(aList))
        if __addon__.getSetting( "AC_Pause" )  == 'true':
            xbmc.Player().pause()
        name = self.getNameByNumber(nummer) or 'Unbekannt'
        self.Notification('Verbindung hergestellt', 'Mit %s [%s]' % (name, nummer))

    def handleDisconnected(self, aList):
        datum, funktion, connectionID, dauer,  leer = aList
        xbmc.log(str(aList))
        self.Notification('Verbindung beendet', 'Dauer: %i Minuten' % (int(int(dauer)/60)))

    def Notification(self, title, text, duration=False, img=False):
        xbmc.log("%s: %s" % (title, text))
        if not duration:
            duration = __addon__.getSetting( "S_DURATION" )
            duration = int(duration)*1000
        if not img:
            img = xbmc.translatePath(os.path.join( xbmcaddon.Addon().getAddonInfo('path'), "media","default.png"))
        return xbmc.executebuiltin('Notification("%s", "%s", %d, "%s")' % (title, str(text), duration, img))

    def start(self):
        ip = __addon__.getSetting( "S_IP" )
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, 1012))
        except Exception, e:
            self.Notification('Fritzbox nicht erreichbar', 'Konnte keine Verbindung zur Fritzbox herstellen (%s)' % e)
        else:
            xbmc.log('connected to fritzbox callmonitor')
            s.settimeout(0.2)
            while not xbmc.abortRequested:
                try:
                    antwort = s.recv(1024)
                    items = antwort.split(';')
                    xbmc.log("[%s] %s" % (ip,antwort))
                    {
                        'CALL': self.handleOutgoingCall,
                        'RING': self.handleIncomingCall,
                        'CONNECT': self.handleConnected,
                        'DISCONNECT': self.handleDisconnected
                    }.get(items[1], self.error)(items)
                except IndexError:
                    xbmc.log('ERROR: Something is wrong with the message from the fritzbox. unexpected firmware maybe')
                except socket.timeout:
                    pass
                except socket.error, e:
                    xbmc.log('ERROR: Could not connect %s on port 1012. Have you activated the Callmonitor via #96*5*' % ip)
                    xbmc.log(pformat(e))
                except Exception, e:
                    xbmc.log(pformat(e))
            s.close()
            xbmc.log("XBMC-Fritzbox Addon beendet.")



FritzCallmonitor().start()