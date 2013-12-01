from pprint import pformat

import xbmc, xbmcaddon
import socket
import os
import re
import datetime
import time

from lib.PytzBox import PytzBox
from lib.PyKlicktel import klicktel
from lib.PyKlicktel import apikey as klicktel_apikey


# Script constants
__addon__ = xbmcaddon.Addon()
__addon_id__ = "service.xbmc-fritzbox"
__version__ = "1"


def _(s):
    """
    @param s: not localized String
    @type  s: string
    """
    translations = {
        'leaving call': 31000,
        'to %s (by %s)': 31001,
        'incoming call': 31002,
        'from %s': 31003,
        'connected': 31004,
        'to %s': 31005,
        'call ended': 31006,
        'duration: %sh': 31007,
        'fritzbox unreachable': 31008,
        'could not connect to fritzbox (%s).': 31009
    }
    if s in translations:
        return __addon__.getLocalizedString(translations[s]) or s
    xbmc.log("UNTRANSLATED: %s" % s)
    return s


class FritzCallMonitor():

    def __init__(self):
        self.__pytzbox = None
        self.__fb_phonebook = None
        self.__autopaused = False
        self.__ring_time = False
        self.__connect_time = False
        self.__klicktel_phonebook = False

        if __addon__.getSetting("AB_Fritzadress") == 'true':
            if self.__pytzbox is None:
                password = False
                if __addon__.getSetting("AB_FritzboxPassword") and len(
                        str(__addon__.getSetting("AB_FritzboxPassword"))) > 0:
                    password = __addon__.getSetting("AB_FritzboxPassword")

                self.__pytzbox = PytzBox.PytzBox(password=password, host=__addon__.getSetting("S_IP"))

                if password:
                    self.__pytzbox.login()

            if self.__fb_phonebook is None:
                self.__fb_phonebook = self.__pytzbox.getPhonebook()

        if __addon__.getSetting("AB_Klicktel") == 'true':
            self.__klicktel_phonebook = klicktel.Klicktel(klicktel_apikey.key())

    def error(*args, **kwargs):
        xbmc.log("ERROR: %s %s" % (args, kwargs))

    class CallMonitorLine(dict):

        command = None

        def __init__(self, response, **kwargs):
            super(FritzCallMonitor.CallMonitorLine, self).__init__(**kwargs)
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

    @staticmethod
    def equal_numbers(a, b):

        a = str(a).strip()
        b = str(b).strip()

        a = str(re.sub('[^0-9]*', '', a))
        b = str(re.sub('[^0-9]*', '', b))

        if a.startswith('00'):
            a = a[4:]
        a = a.lstrip('0')

        if b.startswith('00'):
            b = b[4:]
        b = b.lstrip('0')

        a = a[-len(b):]
        b = b[-len(a):]

        return a == b

    def get_name_by_number(self, request_number):

        if __addon__.getSetting("AB_Fritzadress") == 'true' and self.__fb_phonebook:

            if isinstance(self.__fb_phonebook, dict):
                for entry in self.__fb_phonebook:
                    if 'numbers' in self.__fb_phonebook[entry]:
                        for number in self.__fb_phonebook[entry]['numbers']:
                            if self.equal_numbers(number, request_number):
                                return entry

        if __addon__.getSetting("AB_Klicktel") == 'true' and self.__klicktel_phonebook:

            result = self.__klicktel_phonebook.invers_search(request_number)
            if len(result.entries) > 0:
                name = result.entries[0].displayname
                if name:
                    return name

        return False

    def get_iamge_by_name(self, name):
        if isinstance(self.__fb_phonebook, dict):
            if name in self.__fb_phonebook:
                if "imageHttpURL" in self.__fb_phonebook[name]:
                    return self.__fb_phonebook[name]["imageHttpURL"]
        return False

    def handle_outgoing_call(self, line):
        name = self.get_name_by_number(line.number_called) or str(line.number_called)
        image = self.get_iamge_by_name(name)
        self.show_notification(_('leaving call'), _('to %s (by %s)') % (name, line.number_used), img=image)
        if xbmc.Player().isPlayingVideo():
            self.__ring_time = xbmc.Player().getTime()

    def handle_incoming_call(self, line):
        name = self.get_name_by_number(line.number_caller) or str(line.number_caller)
        image = self.get_iamge_by_name(name)
        self.show_notification(_('incoming call'), _('from %s') % name, img=image)
        if xbmc.Player().isPlayingVideo():
            self.__ring_time = xbmc.Player().getTime()

    def handle_connected(self, line):
        name = self.get_name_by_number(line.number) or str(line.number)
        image = self.get_iamge_by_name(name)
        self.show_notification(_('connected'), _('to %s') % name, img=image)
        if xbmc.Player().isPlayingVideo():
            self.__connect_time = xbmc.Player().getTime()
            if self.__ring_time != self.__connect_time:
                if __addon__.getSetting("AC_Pause") == 'true':
                    xbmc.Player().pause()
                    xbmc.Player().seekTime(self.__ring_time)
                    self.__autopaused = True

    def is_playback_paused(self):
        start_time = xbmc.Player().getTime()
        time.sleep(1)
        if xbmc.Player().getTime() != start_time:
            return False
        else:
            return True

    def resume_playback(self):
        if self.is_playback_paused:
            xbmc.Player().pause()

    def handle_disconnected(self, line):
        self.show_notification(_('call ended'), _('duration: %sh') % str(line.duration))
        if self.__autopaused:
            if __addon__.getSetting("AC_Resume") == 'true':
                self.resume_playback()
            self.__autopaused = False

    @staticmethod
    def show_notification(title, text, duration=False, img=False):
        """
        show xbmc notification

        :rtype : bool
        """
        xbmc.log("NOTIFICATION: %s, %s" % (title, text))
        xbmc.executebuiltin('PingApp')
        if not duration:
            duration = __addon__.getSetting("S_DURATION")
            duration = int(duration) * 1000
        if not img:
            img = xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), "media", "default.png"))
        return xbmc.executebuiltin('Notification("%s", "%s", %d, "%s")' % (title, str(text), duration, img))

    def start(self):
        ip = __addon__.getSetting("S_IP")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, 1012))
        except Exception, e:
            self.show_notification(_('fritzbox unreachable'), _('could not connect to fritzbox (%s).') % e)
        else:
            xbmc.log('connected to fritzbox callmonitor')
            s.settimeout(0.2)

            while not xbmc.abortRequested:

                try:

                    message = s.recv(1024)
                    line = self.CallMonitorLine(message)
                    xbmc.log(str(line))

                    {
                        'CALL': self.handle_outgoing_call,
                        'RING': self.handle_incoming_call,
                        'CONNECT': self.handle_connected,
                        'DISCONNECT': self.handle_disconnected
                    }.get(line.command, self.error)(line)

                except IndexError:
                    xbmc.log('ERROR: Something went wrong with the message from fritzbox. unexpected firmware maybe')

                except socket.timeout:
                    pass

                except socket.error, e:
                    xbmc.log(
                        'ERROR: Could not connect %s on port 1012. Have you activated the Callmonitor via #96*5*' % ip)
                    xbmc.log(pformat(e))

                except Exception, e:
                    xbmc.log(pformat(e))

            s.close()
            xbmc.log("fritzbox callmonitor addon ended.")


if __addon__.getSetting("S_STARTUPSLEEP"):
    time.sleep(int(__addon__.getSetting("S_STARTUPSLEEP")))

FritzCallMonitor().start()
