# Open Source Initiative OSI - The MIT License (MIT):Licensing
#[OSI Approved License]
#The MIT License (MIT)

#Copyright (c) 2011 N.K.
#Copyright (c) 2012 FEP

#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from pprint import pformat
import xbmc, xbmcaddon
import socket
import os
import xml.sax

# Script constants
__addon__       = xbmcaddon.Addon()
__addon_id__    = "service.xbmc-fritzbox"
__author__      = "FEP"
__url__         = "http://code.google.com/p/xbmc-fritzbox"
__version__     = "1"


class FbAbHandler(xml.sax.ContentHandler):

    def __init__(self,tele):
        self.contactname=""
        self.aktiv=None
        self.telefonbuch = tele

    def startElement(self,  name,  attrs):
        if name == "contact":
            self.contactname =""
        elif name == "realName" or name == "number":
            self.aktiv = name

    def endElement (self,  name):
        if name == "realName" or name == "number":
            self.aktiv = None

    def characters(self,  content):
        if self.aktiv == "realName":
            self.contactname = content
        if self.aktiv == "number":
            content.encode()
            self.telefonbuch[content] = self.contactname.encode()



class Fritzboxtelefonbuch():
    def __init__ (self, xbmctele, url):
        self.parser = xml.sax.make_parser()
        self.handler = FbAbHandler(xbmctele)
        self.parser.setContentHandler(self.handler)
        try:
            self.parser.parse(open(url, "r"))
        except IOError:
            print "Datei %s konnte nicht gefunden werden" % url
        except Exception, msg:
            print "Fehler %s aufgetreten" % msg


    def getTelefonbuch(self):
        return self.handler.telefonbuch



class FritzCallmonitor():

    def error(*args, **kwargs):
        xbmc.log("ERROR: %s %s" % (args, kwargs))

    def handleOutgoingCall(self, aList):
        datum, funktion, connectionID, Nebenstelle, GenutzteNummer, AngerufeneNummer, sip,  leer = aList
        xbmc.log(str(aList))
        self.Notification("Ausgehender Anruf", "zu %s (von %s)" % (AngerufeneNummer, GenutzteNummer))

    def getPicByName(self, name):
        PicFolder = __addon__.getSetting( "AB_Pics" )
        PIC = xbmc.translatePath(os.path.join(PicFolder, "%s.png" % name))
        try: open(PIC).close()
        except Exception, e:
            xbmc.log('%s: %s' % (PIC, str(e)))
            PIC = False
        return PIC

    def getNameByNumber(self, number):
        return xbmctelefonbuch.get(number,'Unbenannt')

    def handleIncomingCall(self, aList):
        xbmc.log(str(aList))
        number = aList[3]
        name = self.getNameByNumber(number)
        picture = self.getPicByName(name)
        self.Notification('Eingehender Anruf', 'Von %s [%s]' % (name, number), img=picture)

    def handleConnected(self, aList):
        datum, funktion, connectionID, nebenstelle, nummer, leer = aList
        xbmc.log(str(aList))
        if __addon__.getSetting( "AC_Pause" )  == 'true':
            xbmc.Player().pause()
        self.Notification('Verbindung hergestellt', 'Mit %s' % nummer)

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


xbmctelefonbuch = {}
if __addon__.getSetting( "AB_Fritzadress" ) == 'true':
    xbmctelefonbuch = Fritzboxtelefonbuch(xbmctelefonbuch, __addon__.getSetting( "AB_Adressbookpath")).getTelefonbuch()

FritzCallmonitor().start()