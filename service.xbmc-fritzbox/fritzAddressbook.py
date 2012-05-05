import xml.sax

# Open Source Initiative OSI - The MIT License (MIT):Licensing
#[OSI Approved License]
#The MIT License (MIT)

#Copyright (c) 2012 N.K.

#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# ################################################################################
# author: nk
# version: 0.2
# ################################################################################


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
            content.encode()
            self.telefonbuch[content] = self.contactname.encode()

        

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
