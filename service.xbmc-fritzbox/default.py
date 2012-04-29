import xbmc
from service import FritzCaller


xbmc.log("service.xbmc-fritzbox: ShowCallerInfo-Service starting...")

FritzCaller().startService()
while (not xbmc.abortRequested):
  xbmc.sleep(100)

if xbmc.abortRequested:
    FritzCaller.stopService()

xbmc.log("service.xbmc-fritzbox: ShowCallerInfo-Service stopping...")