import xml.sax.saxutils

class FbAbHandler(xml.sax.ContentHandler):
    
    def __init__(self):
        self.contactname=""
        self.telefonbuch = {}
        self.aktiv=None
        
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

parser = xml.sax.make_parser()
handler = FbAbHandler()
parser.setContentHandler(handler)
parser.parse(open("FRITZ.Box_Telefonbuch.xml", "r"))

nummer = '01710000000' #Flash's Phonenumber ;-)
displayname = handler.telefonbuch.get(nummer, 'unbekannt')
print ('Die nummer %s gehoert: %s ' % (nummer, displayname))
