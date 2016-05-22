# encoding: utf-8

import xbmcaddon
import xbmcgui
import xbmc
import sys
import time
import re
import socket
import traceback

from lib.PytzBox import PytzBox

__addon__ = xbmcaddon.Addon()
__addon_id__ = "service.kodi-fritzbox-callmonitor"
__version__ = "1"


def _(s):
    """
    @param s: not localized String
    @type  s: string
    """
    translations = {
        'fritzbox unreachable': 30408,
        'could not connect to fritzbox': 30415,
        'fritzbox phonebookaccess failed': 30412,
        'resume': 30413,
        'continue in %d sec': 30414,
        'connection successful': 30416,
        'result': 30417,
        'reboot to use new settings': 30418,
        'loaded %d phone book entries': 30419
    }
    if s in translations:
        return __addon__.getLocalizedString(translations[s]) or s
    xbmc.log("UNTRANSLATED: %s" % s)
    return s


def is_playback_paused():
    return bool(xbmc.getCondVisibility("Player.Paused"))


def show_resume_progress_and_resume(wait=10.0):
    dialog = xbmcgui.DialogProgress()
    dialog.create(_('resume'))
    dialog.update(0)

    wait = float(wait)
    remaining = wait

    while remaining > 0:
        dialog.update(100 - int(remaining * 100 / wait),
                      _('continue in %d sec') % int(remaining))

        if not dialog.iscanceled():
            remaining -= 0.05
            time.sleep(0.05)
        else:
            break

    if not dialog.iscanceled():
        if is_playback_paused():
            xbmc.Player().pause()

    dialog.close()


def run_fritzaddress_config_test():
    if __addon__.getSetting("Addressbook_Fritzadress") == 'true':

        password = False
        if __addon__.getSetting("Addressbook_Fritzadress_Password"):
            password = __addon__.getSetting("Addressbook_Fritzadress_Password")

        if __addon__.getSetting("Addressbook_Fritzadress_Username") and \
           len(str(__addon__.getSetting("Addressbook_Fritzadress_Username"))) > 0:
            username = __addon__.getSetting("Addressbook_Fritzadress_Username")
        else:
            username = "admin"

        pytzbox = PytzBox.PytzBox(password=password,
                                  username=username,
                                  host=__addon__.getSetting("Monitor_Address"))

        try:
            if __addon__.getSetting("Addressbook_Fritzadress_book_all") == 'true':
                fritzbox_phonebook = pytzbox.getPhonebook(id=-1)
            else:
                fritzbox_phonebook = pytzbox.getPhonebook(
                    id=int(__addon__.getSetting("Addressbook_Fritzadress_book_id")))

            xbmcgui.Dialog().ok(
                _('result'),
                _('connection successful'),
                _('loaded %d phone book entries') % len(fritzbox_phonebook),
                _('reboot to use new settings'))

        except Exception, e:
            xbmcgui.Dialog().ok(_('result'), _('fritzbox phonebookaccess failed') % e)

            # noinspection PyBroadException
            try:
                if isinstance(e, ValueError) and hasattr(e, 'content'):
                    xbmc.log('FRITZBOX-CALLMONITOR: ' + str(e.content), level=xbmc.LOGERROR)
                xbmc.log('FRITZBOX-CALLMONITOR: ' + traceback.format_exc())
            except:
                pass

def run_fritzmonitor_config_test():
    ip = __addon__.getSetting("Monitor_Address")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, 1012))
    except Exception, e:
        xbmcgui.Dialog().ok(_('result'), _('could not connect to fritzbox'), unicode(e))
        xbmc.log('FRITZBOX-CALLMONITOR: ' + traceback.format_exc())
    else:
        xbmcgui.Dialog().ok(_('result'), _('connection successful'), _('reboot to use new settings'))


match = re.match(r'^(?P<scheme>\w+)://(?P<plugin>[^/]+)/(?P<command>[^/]+)/?(?P<args>.*)$', sys.argv[0])
if match:
    if match.group('command') == 'show_resume_progress_and_resume':
        show_resume_progress_and_resume(float(match.group('args')))
    elif match.group('command') == 'run_fritzmonitor_config_test':
        run_fritzmonitor_config_test()
    elif match.group('command') == 'run_fritzaddress_config_test':
        run_fritzaddress_config_test()
