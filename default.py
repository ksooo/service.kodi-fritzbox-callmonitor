# encoding: utf-8

import xbmc, xbmcaddon, xbmcvfs, xbmcgui
import socket
import os
import re
import datetime
import time
import json
import traceback
import hashlib

from lib.PytzBox import PytzBox
from lib.PyKlicktel import klicktel
from lib.PyKlicktel import apikey as klicktel_apikey
from lib.simple_gdata import SimpleGdataRequest

# Script constants
__addon__ = xbmcaddon.Addon()
__addon_id__ = __addon__.getAddonInfo('id')
__version__ = "1"


def _(s):
    """
    @param s: not localized String
    @type  s: string
    """
    translations = {
        'leaving call': 30400,
        'to %s (by %s)': 30401,
        'incoming call': 30402,
        'from %s': 30403,
        'connected': 30404,
        'to %s': 30405,
        'call ended': 30406,
        'duration: %sh': 30407,
        'fritzbox unreachable': 30408,
        'could not connect to fritzbox (%s).': 30409,
        'unknown': 30410,
        'fritzbox phonebook': 30411,
        'fritzbox phonebookaccess failed': 30412
    }
    if s in translations:
        return __addon__.getLocalizedString(translations[s]) or s
    xbmc.log("FRITZBOX-CALLMONITOR-UNTRANSLATED: %s" % s)
    return s


class FritzCallMonitor():
    def __init__(self):
        self.__pytzbox = None
        self.__fb_phonebook = None
        self.__auto_paused = False
        self.__auto_volume_lowered = False
        self.__connections = dict()
        self.__ring_time = False
        self.__gdata_request = None
        self.__klicktel_phonebook = None

        if __addon__.getSetting("Addressbook_Fritzadress") == 'true':
            if self.__pytzbox is None:

                password = False
                if __addon__.getSetting("Addressbook_Fritzadress_Password"):
                    password = __addon__.getSetting("Addressbook_Fritzadress_Password")

                if __addon__.getSetting("Addressbook_Fritzadress_Username") and \
                   len(str(__addon__.getSetting("Addressbook_Fritzadress_Username"))) > 0:
                    username = __addon__.getSetting("Addressbook_Fritzadress_Username")
                else:
                    username = "admin"

                encrypt = True if __addon__.getSetting("Adressbook_Fritzadress_SSL").upper() == 'TRUE' else False

                self.__pytzbox = PytzBox.PytzBox(password=password,
                                                 username=username,
                                                 host=__addon__.getSetting("Monitor_Address"),
                                                 encrypt=encrypt)

            if self.__fb_phonebook is None:
                try:
                    if __addon__.getSetting("Addressbook_Fritzadress_book_all") == 'true':
                        self.__fb_phonebook = self.__pytzbox.getPhonebook(id=-1)
                    else:
                        self.__fb_phonebook = self.__pytzbox.getPhonebook(
                            id=int(__addon__.getSetting("Addressbook_Fritzadress_book_id")))
                    xbmc.log(u"FRITZBOX-CALLMONITOR: loaded %d phone book entries" % len(self.__fb_phonebook))
                except Exception, e:
                    self.show_notification(_('fritzbox phonebook'), _('fritzbox phonebookaccess failed') % str(e))
                    xbmc.log('FRITZBOX-CALLMONITOR: ' + traceback.format_exc(), level=xbmc.LOGERROR)
                    if isinstance(e, PytzBox.XMLValueError):
                        xbmc.log(repr(e.content), level=xbmc.LOGERROR)
                    # noinspection PyBroadException
                    try:
                        if isinstance(e, ValueError) and hasattr(e, 'content'):
                            xbmc.log('FRITZBOX-CALLMONITOR: ' + str(e.content), level=xbmc.LOGERROR)
                        xbmc.log('FRITZBOX-CALLMONITOR: ' + traceback.format_exc())
                    except:
                        pass

        if __addon__.getSetting("Addressbook_Google") == 'true':
            self.__gdata_request = SimpleGdataRequest.SimpleGdataRequest()
            # noinspection PyBroadException
            try:
                self.__gdata_request.authorize(__addon__.getSetting("Addressbook_Google_Username"),
                                               __addon__.getSetting("Addressbook_Google_Password"), 'cp')
            except Exception:
                xbmc.log('FRITZBOX-CALLMONITOR: ' + traceback.format_exc())

        if __addon__.getSetting("Addressbook_Klicktel") == 'true':
            self.__klicktel_phonebook = klicktel.Klicktel(klicktel_apikey.key())

    def error(*args, **kwargs):
        xbmc.log("FRITZBOX-CALLMONITOR: %s %s" % (args, kwargs))

    class CallMonitorLine(dict):

        class UnexpectedCommandException(Exception):
            pass

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

            else:
                raise self.UnexpectedCommandException(self.command)

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

        def __repr__(self):
            return self.command.lower() + ' event: ' + ', '.join(["%s=%s" % (key, self[key]) for key in self.keys()])

    @staticmethod
    def equal_numbers(a, b):

        a = unicode(a).strip()
        b = unicode(b).strip()

        a = re.sub('[^0-9]*', '', a)
        b = re.sub('[^0-9]*', '', b)

        if a.startswith('00'):
            a = a[4:]
        a = a.lstrip('0')

        if b.startswith('00'):
            b = b[4:]
        b = b.lstrip('0')

        if len(b) * 2 < len(a) or len(a) < len(b) / 2:
            return False

        a = a[-len(b):]
        b = b[-len(a):]

        return a == b

    def is_ignored_number(self, number, printout=False):
        if not isinstance(number, list):
            number = [number, ]
        for single_number in number:
            for ignored_number in re.findall(r'(\d+)', __addon__.getSetting("Monitor_IgnoreNumbers")):
                if self.equal_numbers(single_number, ignored_number):
                    if printout:
                        print "%s is ignored" % single_number
                    return single_number
        return False

    def get_name_by_number(self, request_number):

        if not len(request_number):
            return _('unknown')

        if __addon__.getSetting("Addressbook_Fritzadress") == 'true' and self.__fb_phonebook:
            if isinstance(self.__fb_phonebook, dict):
                for entry in self.__fb_phonebook:
                    if 'numbers' in self.__fb_phonebook[entry]:
                        for number in self.__fb_phonebook[entry]['numbers']:
                            if self.equal_numbers(number, request_number):
                                return entry

        if __addon__.getSetting("Addressbook_Klicktel") == 'true' and self.__klicktel_phonebook:
            result = self.__klicktel_phonebook.invers_search(request_number)
            if len(result.entries) > 0:
                name = result.entries[0].displayname
                if name:
                    return name

        return False

    def get_image_by_name(self, name, number):

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

        if __addon__.getSetting("Addressbook_Folderimages") == 'true':
            imagepath = __addon__.getSetting("Addressbook_Folderimages_Path").decode('utf-8', 'replace')
            if not xbmcvfs.exists(imagepath):
                xbmc.log("FRITZBOX-CALLMONITOR: Images path %s does not exist.") % imagepath.encode('utf-8')
            else:
                dirs, files = xbmcvfs.listdir(imagepath)
                for picture in files:
                    picture = picture.decode('utf-8', 'replace')
                    match = re.match(r'([^.]*)', picture)
                    if re.match:
                        file_short_name = match.group(1)
                        if file_short_name == name or self.equal_numbers(file_short_name, number):
                            return u"%s%s" % (imagepath, picture)

        if isinstance(self.__fb_phonebook, dict):
            if name in self.__fb_phonebook:
                if "imageHttpURL" in self.__fb_phonebook[name]:

                    if self.__fb_phonebook[name]["imageHttpURL"].startswith('https://www.google.com/'):
                        # noinspection PyBroadException
                        try:
                            return get_google_image(self.__fb_phonebook[name]["imageHttpURL"])
                        except Exception:
                            xbmc.log('FRITZBOX-CALLMONITOR: ' + traceback.format_exc())
                    else:
                        return self.__fb_phonebook[name]["imageHttpURL"]

        return False

    @staticmethod
    def is_playback_paused():
        return bool(xbmc.getCondVisibility("Player.Paused"))

    def resume_playback(self, delay):
        if self.is_playback_paused():

            if int(__addon__.getSetting("Action_OnHangup_Resume_Delay")) > 0:
                url = "plugin://%s/show_resume_progress_and_resume/%d" % (
                    __addon_id__, delay)
                xbmc.executebuiltin('XBMC.RunPlugin("%s")' % url)
            else:
                xbmc.Player().pause()

    def pause(self, video_playback_only):

        if not xbmc.Player().isPlaying():
            return False

        if self.is_playback_paused():
            return False

        if video_playback_only and not xbmc.Player().isPlayingVideo():
            return False

        xbmc.Player().pause()
        if self.__ring_time:
            xbmc.Player().seekTime(self.__ring_time)
        self.__auto_paused = True

        return True

    def lower_volume(self, amount):
        volume_json = xbmc.executeJSONRPC(json.dumps(
            dict(jsonrpc="2.0", method="Application.GetProperties", params=dict(properties=["volume", ]), id=1)))
        if "result" in json.loads(volume_json):
            volume = json.loads(volume_json)["result"]["volume"]
            new_volume = int(volume - (int(float(amount)) * volume / 100))

            if volume:
                if not self.__auto_volume_lowered:
                    self.__auto_volume_lowered = volume
                xbmc.executeJSONRPC(json.dumps(
                    dict(jsonrpc="2.0", method="Application.SetVolume", params=dict(volume=new_volume), id=1)))

    def reset_volume(self):
        if self.__auto_volume_lowered:
            xbmc.executeJSONRPC(json.dumps(
                dict(jsonrpc="2.0", method="Application.SetVolume", params=dict(volume=self.__auto_volume_lowered),
                     id=1)))
            self.__auto_volume_lowered = False

    def handle_outgoing_call(self, line):

        if self.is_ignored_number([line.number_caller, line.number_called], printout=True):
            return False
        else:
            self.__connections[line.connection_id] = line

        name = self.get_name_by_number(line.number_called) or str(line.number_called)
        image = self.get_image_by_name(name, line.number_called)

        if __addon__.getSetting("Action_OnLeaving_Notify") == 'true':
            self.show_notification(_('leaving call'), _('to %s (by %s)') % (name, line.number_caller), img=image)

        if xbmc.Player().isPlayingVideo():
            self.__ring_time = xbmc.Player().getTime()

        if __addon__.getSetting("Action_OnLeaving_Pause") == 'true':
            self.pause(video_playback_only=__addon__.getSetting("Action_OnLeaving_Pause_VideoOnly") == 'true')

    def handle_incoming_call(self, line):

        if self.is_ignored_number([line.number_caller, line.number_called], printout=True):
            return False
        else:
            self.__connections[line.connection_id] = line

        name = self.get_name_by_number(line.number_caller) or str(line.number_caller)
        image = self.get_image_by_name(name, line.number_caller)

        if __addon__.getSetting("Action_OnRing_Notify") == 'true':
            self.show_notification(_('incoming call'), _('from %s') % name, img=image)

        if __addon__.getSetting("Action_OnRing_LowerVolume") == 'true':
            self.lower_volume(__addon__.getSetting("Action_OnRing_LowerVolume_Amount"))

        if __addon__.getSetting("Action_OnRing_Pause") == 'true':
            self.pause(video_playback_only=__addon__.getSetting("Action_OnRing_Pause_VideoOnly") == 'true')

        if xbmc.Player().isPlayingVideo():
            self.__ring_time = xbmc.Player().getTime()

    def handle_connected(self, line):

        if not line.connection_id in self.__connections:
            return False

        name = self.get_name_by_number(line.number) or str(line.number)
        image = self.get_image_by_name(name, line.number)

        if __addon__.getSetting("Action_OnConnect_Notify") == 'true':
            self.show_notification(_('connected'), _('to %s') % name, img=image)

        if __addon__.getSetting("Action_OnConnect_LowerVolume") == 'true':
            self.lower_volume(__addon__.getSetting("Action_OnConnect_LowerVolume_Amount"))

        if __addon__.getSetting("Action_OnConnect_Pause") == 'true':
            self.pause(video_playback_only=__addon__.getSetting("Action_OnConnect_Pause_VideoOnly") == 'true')

    def handle_disconnected(self, line):

        if not line.connection_id in self.__connections:
            return False

        if __addon__.getSetting("Action_OnHangup_Notify") == 'true':
            self.show_notification(_('call ended'), _('duration: %sh') % str(line.duration))

        if __addon__.getSetting("Action_OnHangup_ResetVolume") == 'true':
            self.reset_volume()

        if __addon__.getSetting("Action_OnHangup_Resume") == 'true':
            if self.__auto_paused:
                self.__auto_paused = False
                self.resume_playback(delay=int(__addon__.getSetting("Action_OnHangup_Resume_Delay")))

        del self.__connections[line.connection_id]

    @staticmethod
    def show_notification(title, text, duration=False, img=False):
        """
        show xbmc notification

        :rtype : bool
        """
        if isinstance(title, str):
            title = unicode(title)
        if isinstance(text, str):
            text = unicode(text)

        xbmc.log((u"FRITZBOX-CALLMONITOR-NOTIFICATION: %s, %s" % (title, text)).encode("utf-8"))
        if xbmc.getCondVisibility("System.ScreenSaverActive"):
            xbmc.executebuiltin('ActivateWindow(%s)' % xbmcgui.getCurrentWindowId())
        if not duration:
            duration = __addon__.getSetting("Action_Notification_Duration")
            duration = int(duration) * 1000
        if not img:
            img = xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path'), "media", "default.png"))
        return xbmc.executebuiltin((u'Notification("%s", "%s", %d, "%s")' %
                                    (title, text, duration, img)).encode("utf-8"))

    @staticmethod
    def __sleep(duration=5):
        for i in range(duration * 10):
            time.sleep(0.1)
            if xbmc.abortRequested:
                break

    def start(self):
        """
        start call monitor process

        :rtype : bool
        """

        ip = __addon__.getSetting("Monitor_Address")
        xbmc.log('FRITZBOX-CALLMONITOR: started')
        connection_ready_notification = False
        connection_failed_notification = False

        # noinspection PyBroadException
        try:

            while not xbmc.abortRequested:

                try:
                    box_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    box_socket.connect((ip, 1012))
                    box_socket.settimeout(0.2)
                    if not connection_ready_notification:
                        xbmc.log('FRITZBOX-CALLMONITOR: connected')
                        connection_ready_notification = True
                        connection_failed_notification = False

                except socket.error, e:
                    if not connection_failed_notification:
                        #self.show_notification(
                        #    _('fritzbox unreachable'),
                        #    _('could not connect to fritzbox (%s).') % str(e))
                        connection_ready_notification = False
                        #connection_failed_notification = True
                        #xbmc.log('FRITZBOX-CALLMONITOR: could not connect %s on port 1012 (%s)' % (ip, e))
                        #xbmc.log('FRITZBOX-CALLMONITOR: do you have activated the callmonitor via #96*5* ' +
                        #         'and a valid network connection?')
                    self.__sleep()

                else:
                    try:
                        for _ in range(20):  # 20 * 0.2 sec
                            try:
                                message = box_socket.recv(1024)
                                line = self.CallMonitorLine(message)
                                xbmc.log("FRITZBOX-CALLMONITOR: %s" % str(line))
                                {'CALL': self.handle_outgoing_call,
                                 'RING': self.handle_incoming_call,
                                 'CONNECT': self.handle_connected,
                                 'DISCONNECT': self.handle_disconnected
                                 }.get(line.command, self.error)(line)
                                if xbmc.abortRequested:
                                    break

                            except socket.timeout:
                                # this is absolute normal an occurs every 0.2 seconds
                                pass

                    except socket.error, e:
                        # connection disrupted, wait a while and retry
                        connection_ready_notification = False
                        connection_failed_notification = False
                        xbmc.log('FRITZBOX-CALLMONITOR: connection disrupted: %s' % e)
                        self.__sleep()

                    finally:
                        box_socket.close()

        except FritzCallMonitor.CallMonitorLine.UnexpectedCommandException, e:
            xbmc.log('FRITZBOX-CALLMONITOR: something went wrong with the message from fritzbox (%s). ' +
                     'unexpected firmware maybe' % e)

        except Exception:
            xbmc.log('FRITZBOX-CALLMONITOR: ' + traceback.format_exc(), level=xbmc.LOGERROR)

        finally:
            xbmc.log("FRITZBOX-CALLMONITOR: addon ended.")


xbmc.log("{0:s} version {1:s} ({2:s}:{3:d})"
         .format(__addon__.getAddonInfo('name'),
                 __addon__.getAddonInfo('version'),
                 hashlib.md5(open(__file__).read()).hexdigest(),
                 int(os.path.getmtime(__file__))))

FritzCallMonitor().start()
