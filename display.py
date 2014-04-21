# encoding: utf-8

import xbmcaddon
import xbmcgui
import xbmc
import sys
import time
import re

__addon__ = xbmcaddon.Addon()
__addon_id__ = "service.xbmc-fritzbox"
__version__ = "1"


def _(s):
    """
    @param s: not localized String
    @type  s: string
    """
    translations = {
        'resume': 31013,
        'continue in %d sec': 31014
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


match = re.match(r'^(?P<scheme>\w+)://(?P<plugin>[^/]+)/(?P<command>[^/]+)/?(?P<args>.*)$', sys.argv[0])
if match:
    if match.group('command') == 'show_resume_progress_and_resume':
        show_resume_progress_and_resume(float(match.group('args')))