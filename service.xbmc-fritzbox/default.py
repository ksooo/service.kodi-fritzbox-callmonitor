import xbmc
from service import FritzCaller


xbmc.log("service.xbmc-fritzbox: ShowCallerInfo-Service starting...")

fritz = FritzCaller()
fritz.startService()
while (not xbmc.abortRequested):
  xbmc.sleep(100)
  if (xbmc.abortRequested):
      fritz.stopService()
      xbmc.log("service.xbmc-fritzbox: Aborting...")
      break


xbmc.log("service.xbmc-fritzbox: ShowCallerInfo-Service stopping...")