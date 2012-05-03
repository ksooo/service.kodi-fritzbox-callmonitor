import xml.sax

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
            self.telefonbuch[content] = self.contactname

        

class Fritzboxtelefonbuch():
    def __init__ (self,xbmctele,url):       
        self.parser = xml.sax.make_parser()
        self.handler = FbAbHandler(xbmctele)
        self.parser.setContentHandler(self.handler)
        try:
            self.parser.parse(open(url, "r"))
        except IOError:
            print "Datei %s konnte nicht gefunden werden" %(url)
        except error, msg:
            print "Fehler %s aufgetreten" %(msg)
        
    
    def getTelefonbuch(self):
        return self.handler.telefonbuch

#nummer = '01710000000' #Flash's Phonenumber ;-)
#displayname = handler.telefonbuch.get(nummer, 'Unbekannt')
#print ('Die nummer %s gehoert: %s ' % (nummer, displayname))
