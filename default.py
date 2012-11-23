from pprint import pformat

import xbmc, xbmcaddon
import socket
import os
import re
import datetime
import time

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

    class CallMonitorLine(dict):

        command = None

        def __init__(self, response, **kwargs):

            self.__responses = dict()
            if isinstance(response, str) or isinstance(response, unicode):
                response = response.split(';')
            self.command = response[1]

            if self.command == 'CALL':
                self['date'] = response[0]
                self['connection_id'] = response[2]
                self['extension'] = response[3]
                self['number_used'] = response[4]
                self['number_called'] = response[5]
                self['sip'] = response[6]

            elif self.command == 'RING':
                self['date'] = response[0]
                self['connection_id'] = response[2]
                self['number_caller'] = response[3]
                self['number_called'] = response[4]
                self['sip'] = response[5]

            elif self.command == 'CONNECT':
                self['date'] = response[0]
                self['connection_id'] = response[2]
                self['extension'] = response[3]
                self['number'] = response[4]

            elif self.command == 'DISCONNECT':
                self['date'] = response[0]
                self['connectionID'] = response[2]
                self['duration'] = response[3]


            if 'date' in self:
                #noinspection PyBroadException
                try:
                    self['date'] = datetime.datetime.strptime(self['date'].strip(), '%d.%m.%y %H:%M:%S')
                except Exception:
                    pass

            if 'duration' in self:
                #noinspection PyBroadException
                try:
                    self['duration'] = datetime.timedelta(seconds=int(self['duration']))
                except Exception:
                    pass


        def __getattr__(self, item):
            if item in self:
                return self[item]
            else:
                return False


    def equalNumbers(self, a, b):
        a = str(a).strip()
        b = str(b).strip()

        a = str(re.sub('[^0-9]*', '', a))
        b = str(re.sub('[^0-9]*', '', b))

        if a.startswith('00'): a = a[4:]
        a = a.lstrip('0')

        if b.startswith('00'): b = b[4:]
        b = b.lstrip('0')

        a = a[-len(b):]
        b = b[-len(a):]

        return (a == b)


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
                            if self.equalNumbers(number, request_number):
                                return entry

        return False



    def handleOutgoingCall(self, line):
        name = self.getNameByNumber(line.number_called) or 'Unbekannt'
        self.Notification("Ausgehender Anruf", "zu %s [%s] (von %s)" % (name, line.number_called, line.number_used))

    def handleIncomingCall(self, line):
        name = self.getNameByNumber(line.number_caller) or 'Unbekannt'
        self.Notification('Eingehender Anruf', 'Von %s [%s]' % (name, line.number_caller))

    def handleConnected(self, line):
        if __addon__.getSetting( "AC_Pause" )  == 'true':
            xbmc.Player().pause()
        name = self.getNameByNumber(line.number) or 'Unbekannt'
        self.Notification('Verbindung hergestellt', 'Mit %s [%s]' % (name, line.number))

    def handleDisconnected(self, line):
        self.Notification('Verbindung beendet', 'Dauer: %sh' % str(line.duration))

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

                    message = s.recv(1024)
                    line = self.CallMonitorLine(message)
                    xbmc.log(str(line))

                    {
                        'CALL': self.handleOutgoingCall,
                        'RING': self.handleIncomingCall,
                        'CONNECT': self.handleConnected,
                        'DISCONNECT': self.handleDisconnected
                    }.get(line.command, self.error)(line)

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


if __addon__.getSetting( "S_STARTUPSLEEP" ):
    time.sleep(int(__addon__.getSetting( "S_STARTUPSLEEP" )))

FritzCallmonitor().start()