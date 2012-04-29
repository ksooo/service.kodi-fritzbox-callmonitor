# Open Source Initiative OSI - The MIT License (MIT):Licensing
#[OSI Approved License]
#The MIT License (MIT)

#Copyright (c) 2011 N.K.

#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import sqlite3
import string


class Person(object):
    #private vars
    def __init__(self, aFirstname, aLastname): 
        self.__mFirstName = aFirstname
        self.__mLastName = aLastname
        
    def getName(self):
        return self.__mFirstname + self.__mLastname
    
    def getFirstname(self):
        return self.__mFirstName
    
    def getLastname(self):
        return self.__mLastName
    
class Address(object):
    def __init__(self,aStreet,aNr,aZip):
        self.__mStreet = aStreet
        self.__mNr = aNr
        self.__mZip = aZip

class Telephone(object):
    def __init__(self):
        self.__mDict = []
        #[Description,Nummer]
        
class Category(object):
    def __init__(self):
        self.__mCat = ''


AddressDB = '/home/mainuser/iphone/AddressBook.sqlitedb'
AddressConnection=sqlite3.connect(AddressDB)
Addresscursor=AddressConnection.cursor()
Addresscursor.execute('SELECT ROWID, First, Last FROM ABPerson')
Addressentries=Addresscursor.fetchall()
print Addressentries
Addresscursor.close()
TelNrCursor = AddressConnection.cursor()
TelNrCursor.execute('SELECT record_id, value FROM ABMultiValue')
TelNrs = TelNrCursor.fetchall()
print TelNrs
TelNrCursor.close()
for persID,persNr in TelNrs:
    
    print type(persNr)

AddressDBImg = '/home/mainuser/iphone/AddressBookImages.sqlitedb'
connection=sqlite3.connect(AddressDBImg)
cursor=connection.cursor()
cursor.execute('SELECT data FROM ABThumbnailImage')
allIMG =  cursor.fetchall()
print allIMG
inte=0
for data in allIMG:
    print data
    inte += 1
    theIMG = data [0]
    if theIMG:
        filename = ('/home/mainuser/iphone/Thumb%i.jpg' % (inte))
        fout = open(filename,'wb')
        fout.write(theIMG)

#allentries=cursor.fetchall()
#print allentries
#print allentries[0]

cursor.close()
quit()
fout.close()
