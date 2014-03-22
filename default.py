# encoding: utf-8
from pprint import pformat

import xbmc, xbmcaddon
import socket
import os
import re
import datetime
import time
import hashlib
import pprint
import json
import traceback

from lib.PytzBox import PytzBox
from lib.PyKlicktel import klicktel
from lib.PyKlicktel import apikey as klicktel_apikey
from lib.simple_gdata import SimpleGdataRequest

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
        self.__autovolumelowered = False
        self.__connections = dict()
        self.__ring_time = False
        self.__gdata_request = None
        self.__klicktel_phonebook = None

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
                self.__fb_phonebook = dict()
                if __addon__.getSetting("AB_Fritzadress_all_books") == 'true':
                    phonebook_list = self.__pytzbox.getPhonebookList()
                    if not phonebook_list or len(phonebook_list) < 0:
                        phonebook_list = [0]
                    for phonebook_id in phonebook_list:
                        self.__fb_phonebook.update(
                            self.__pytzbox.getPhonebook(id=phonebook_id))
                else:
                    self.__fb_phonebook.update(
                        self.__pytzbox.getPhonebook(id=int(__addon__.getSetting("AB_Fritzadress_id"))))
                xbmc.log(u"loaded %d phone book entries" % len(self.__fb_phonebook))

        if __addon__.getSetting("AB_GoogleLookup") == 'true':
            self.__gdata_request = SimpleGdataRequest.SimpleGdataRequest()
            try:
                self.__gdata_request.authorize(__addon__.getSetting("AB_GoogleUsername"),
                                               __addon__.getSetting("AB_GooglePassword"), 'cp')
            except Exception, e:
                xbmc.log(pprint.pformat(e))

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
                self['connection_id'] = int(response[2])
                self['extension'] = response[3]
                self['number_caller'] = response[4]
                self['number_called'] = response[5]
                self['sip'] = response[6]

            elif self.command == 'RING':
                self['date'] = response[0]
                self['connection_id'] = int(response[2])
                self['number_caller'] = response[3]
                self['number_called'] = response[4]
                self['sip'] = response[5]

            elif self.command == 'CONNECT':
                self['date'] = response[0]
                self['connection_id'] = int(response[2])
                self['extension'] = response[3]
                self['number'] = response[4]

            elif self.command == 'DISCONNECT':
                self['date'] = response[0]
                self['connection_id'] = int(response[2])
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

    def is_ignored_number(self, number, printout=False):
        if not isinstance(number, list):
            number = [number, ]
        for single_number in number:
            for ignored_number in re.findall(r'(\d+)', __addon__.getSetting("AB_IgnoreNumbers")):
                if self.equal_numbers(single_number, ignored_number):
                    if printout:
                        print "%s is ignored" % single_number
                    return single_number
        return False

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

    def get_image_by_name(self, name):

        def get_google_image(url):
            url = re.sub(r',\d*$', '', url)
            m = hashlib.md5()
            m.update(url)
            file_name = m.hexdigest()
            file_path = os.path.join(xbmc.translatePath('special://temp'),
                                     "%s_%s" % (__addon__.getAddonInfo('id'), file_name))

            if not os.path.isfile(file_path):
                image = self.__gdata_request.request(url, pretty=False)
                file_handler = open(file_path, 'wb')
                file_handler.write(image)
                file_handler.close()

            return file_path

        if isinstance(self.__fb_phonebook, dict):
            if name in self.__fb_phonebook:
                if "imageHttpURL" in self.__fb_phonebook[name]:

                    if self.__fb_phonebook[name]["imageHttpURL"].startswith('https://www.google.com/'):
                        try:
                            return get_google_image(self.__fb_phonebook[name]["imageHttpURL"])
                        except Exception, e:
                            xbmc.log(pprint.pformat(e))
                    else:
                        return self.__fb_phonebook[name]["imageHttpURL"]

        return False

    @staticmethod
    def is_playback_paused():
        return bool(xbmc.getCondVisibility("Player.Paused"))

    def resume_playback(self):
        if self.is_playback_paused():
            xbmc.Player().pause()

    def handle_outgoing_call(self, line):

        if self.is_ignored_number([line.number_caller, line.number_called], printout=True):
            return False
        else:
            self.__connections[line.connection_id] = line

        name = self.get_name_by_number(line.number_called) or str(line.number_called)
        image = self.get_image_by_name(name)
        self.show_notification(_('leaving call'), _('to %s (by %s)') % (name, line.number_caller), img=image)
        if xbmc.Player().isPlayingVideo():
            self.__ring_time = xbmc.Player().getTime()

    def handle_incoming_call(self, line):

        if self.is_ignored_number([line.number_caller, line.number_called], printout=True):
            return False
        else:
            self.__connections[line.connection_id] = line

        name = self.get_name_by_number(line.number_caller) or str(line.number_caller)
        image = self.get_image_by_name(name)

        self.show_notification(_('incoming call'), _('from %s') % name, img=image)
        if xbmc.Player().isPlayingVideo():
            self.__ring_time = xbmc.Player().getTime()

        if __addon__.getSetting("AC_LowerVolume") == 'true':
            volume_json = xbmc.executeJSONRPC(json.dumps(
                dict(jsonrpc="2.0", method="Application.GetProperties", params=dict(properties=["volume", ]), id=1)))
            if "result" in json.loads(volume_json):
                volume = json.loads(volume_json)["result"]["volume"]
                new_volume = int(volume - (int(float(__addon__.getSetting("AC_LowerVolumeAmount"))) * volume / 100))

                if volume:
                    self.__autovolumelowered = volume
                    xbmc.executeJSONRPC(json.dumps(
                        dict(jsonrpc="2.0", method="Application.SetVolume", params=dict(volume=new_volume), id=1)))

    def handle_connected(self, line):

        if not line.connection_id in self.__connections:
            return False

        name = self.get_name_by_number(line.number) or str(line.number)
        image = self.get_image_by_name(name)

        if self.__autovolumelowered:
            xbmc.executeJSONRPC(json.dumps(
                dict(jsonrpc="2.0", method="Application.SetVolume", params=dict(volume=self.__autovolumelowered),
                     id=1)))
            self.__autovolumelowered = False

        self.show_notification(_('connected'), _('to %s') % name, img=image)
        if __addon__.getSetting("AC_Pause") == 'true':
            if __addon__.getSetting("AC_PauseVideoOnly") == 'false' or xbmc.Player().isPlayingVideo():
                if not self.is_playback_paused():
                    xbmc.Player().pause()
                    xbmc.Player().seekTime(self.__ring_time)
                    self.__autopaused = True

    def handle_disconnected(self, line):

        if not line.connection_id in self.__connections:
            return False

        self.show_notification(_('call ended'), _('duration: %sh') % str(line.duration))

        if self.__autovolumelowered:
            xbmc.executeJSONRPC(json.dumps(
                dict(jsonrpc="2.0", method="Application.SetVolume", params=dict(volume=self.__autovolumelowered),
                     id=1)))
            self.__autovolumelowered = False

        if self.__autopaused:
            if __addon__.getSetting("AC_Resume") == 'true':
                self.resume_playback()
            self.__autopaused = False

        del self.__connections[line.connection_id]

    @staticmethod
    def show_notification(title, text, duration=False, img=False):
        """
        show xbmc notification

        :rtype : bool
        """
        if isinstance (title,str):
            title = unicode(title)
        if isinstance(text,str):
            text = unicode(text)

        xbmc.log((u"NOTIFICATION: %s, %s" % (title, text)).encode("utf-8"))
        xbmc.executebuiltin('PingApp')
        if not duration:
            duration = __addon__.getSetting("S_DURATION")
            duration = int(duration) * 1000
        if not img:
            img = xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), "media", "default.png"))
        return xbmc.executebuiltin((u'Notification("%s", "%s", %d, "%s")' % (title, text, duration, img)).encode("utf-8"))

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
                    trace = traceback.format_exc()
                    xbmc.log(trace)

            s.close()
            xbmc.log("fritzbox callmonitor addon ended.")


if __addon__.getSetting("S_STARTUPSLEEP"):
    time.sleep(int(__addon__.getSetting("S_STARTUPSLEEP")))

FritzCallMonitor().start()
