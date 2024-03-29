#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import socket
import xml.sax
import requests
from requests.auth import HTTPDigestAuth
import hashlib
import os

class PytzBox:
    __password = False
    __host = False
    __user = False
    __sid = None
    __sslverify = False
    __encrypt = None
    __imagepath = None
    __imagecount = None

    __url_contact = ['https://{host}:49443/upnp/control/x_contact', 'http://{host}:49000/upnp/control/x_contact']
    __url_file_download = ['https://{host}:49443{imageurl}&sid={sid}', 'http://{host}:49000{imageurl}&sid={sid}']
    __soapaction_phonebooklist = 'urn:dslforum-org:service:X_AVM-DE_OnTel:1#GetPhonebookList'
    __soapenvelope_phonebooklist = '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:GetPhonebookList xmlns:u="urn:dslforum-org:service:X_AVM-DE_OnTel:1"></u:GetPhonebookList></s:Body></s:Envelope>'
    __soapaction_phonebook = 'urn:dslforum-org:service:X_AVM-DE_OnTel:1#GetPhonebook'
    __soapenvelope_phonebook = '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:GetPhonebook xmlns:u="urn:dslforum-org:service:X_AVM-DE_OnTel:1"><NewPhonebookId>{NewPhonebookId}</NewPhonebookId></u:GetPhonebook></s:Body></s:Envelope>'

    class BoxUnreachableException(Exception): pass
    class LoginFailedException(Exception): pass
    class RequestFailedException(Exception): pass
    class InternalServerErrorException(Exception): pass

    def __init__(self, password=False, host="fritz.box", username=False, encrypt=True, imagepath=None):

        socket.setdefaulttimeout(10)

        self.__password = password
        self.__host = host
        self.__user = username
        self.__encrypt = 0 if encrypt else 1
        self.__imagepath = imagepath
        self.__imagecount = 0

    def imagecount(self):
        return self.__imagecount

    def compareNumbers(self, a, b, ccode='0049'):

        a = str(re.sub('[^0-9\+\*]|((?<!\A)\+)', '', a))
        b = str(re.sub('[^0-9\+\*]|((?<!\A)\+)', '', b))

        if a.startswith(ccode): a = '0' + a[len(ccode):]
        if a.startswith('+'): a = '0' + a[3:]

        if b.startswith(ccode): b = '0' + b[len(ccode):]
        if b.startswith('+'): b = '0' + b[3:]

        # a = a[-len(b):]
        # b = b[-len(a):]

        return (a == b)

    def __analyzeFritzboxPhonebook(self, xml_phonebook):

        class FbAbHandler(xml.sax.ContentHandler):

            def __init__(self, parent):
                self.contact_name = ""
                self.key = None
                self.parent = parent
                self.phone_book = dict()

            # noinspection PyUnusedLocal
            def startElement(self, name, args):
                if name == "contact":
                    self.contact_name = ""
                self.key = name

            # noinspection PyUnusedLocal
            def endElement(self, name):
                self.key = None

            def characters(self, content):
                if self.key == "realName":
                    self.contact_name = content
                    if not self.contact_name in self.phone_book:
                        self.phone_book[self.contact_name] = {'numbers': []}
                if self.key == "number":
                    if self.contact_name in self.phone_book:
                        self.phone_book[self.contact_name]['numbers'].append(content)
                if self.key == "imageURL":
                    if self.contact_name in self.phone_book:
                        self.phone_book[self.contact_name]['imageHttpURL'] = self.parent.getDownloadUrl(content)
                        self.phone_book[self.contact_name]['imageBMP'] = self.parent.getImage(content, self.contact_name)

        handler = FbAbHandler(self)

        try:
            xml.sax.parseString(xml_phonebook, handler=handler)
        except Exception as e:
            raise ValueError('could not parse phonebook data (are you logged in?): %s' % e)

        return handler.phone_book

    def getDownloadUrl(self, url):

        return self.__url_file_download[self.__encrypt].format(
            host=self.__host,
            imageurl=url,
            sid=self.__sid
        )

    def getImage(self, url, caller_name):
        if self.__imagepath is None: return
        try:
            response = requests.get(self.__url_file_download[self.__encrypt].format(
                host=self.__host,
                imageurl=url,
                sid=self.__sid
            ))
            if response.status_code == 200:
                imagepath = os.path.join(self.__imagepath, hashlib.md5(caller_name.encode('utf-8')).hexdigest() + '.jpg')
                with open(imagepath, 'wb') as fh: fh.write(response.content)
                self.__imagecount += 1
                return imagepath

        except Exception as e:
            print(e)

    def getPhonebookList(self):

        try:
            response = requests.post(self.__url_contact[self.__encrypt].format(host=self.__host),
                                     auth=HTTPDigestAuth(self.__user, self.__password),
                                     data=self.__soapenvelope_phonebooklist,
                                     headers={'Content-Type': 'text/xml; charset="utf-8"',
                                              'SOAPACTION': self.__soapaction_phonebooklist},
                                     verify=self.__sslverify)

        except socket.error as e:
            raise self.BoxUnreachableException(e)
        except requests.exceptions.ConnectionError as e:
            raise self.BoxUnreachableException(e)
        except Exception as e:
            raise self.RequestFailedException(e)
        else:
            if response.status_code == 200:
                response = response.content
                phonbook_ids = []

                for this_line in re.findall(r'<NewPhonebookList>([\d,]*)</NewPhonebookList>', str(response)):
                    for this_id in this_line.split(','):
                        phonbook_ids.append(int(this_id))

                return list(set(phonbook_ids))
            elif response.status_code == 401:
                raise self.LoginFailedException()
            else:
                raise self.RequestFailedException('Request failed with status code: %s' % response.status_code)

    def getPhonebook(self, id=0, imgpath=None):

        if id == -1:
            result = dict()
            for this_id in self.getPhonebookList():
                if this_id < 0:
                    continue
                result.update(self.getPhonebook(id=this_id))
            return result

        try:
            response = requests.post(self.__url_contact[self.__encrypt].format(host=self.__host),
                                     auth=HTTPDigestAuth(self.__user, self.__password),
                                     data=self.__soapenvelope_phonebook.format(NewPhonebookId=id),
                                     headers={'Content-Type': 'text/xml; charset="utf-8"',
                                              'SOAPACTION': self.__soapaction_phonebook},
                                     verify=self.__sslverify)
        except socket.error as e:
            raise self.BoxUnreachableException(e)
        except requests.exceptions.ConnectionError as e:
            raise self.BoxUnreachableException(e)
        except Exception as e:
            raise self.RequestFailedException(e)
        else:
            if response.status_code == 200:
                response = response.content
                phonbook_urls = re.findall(r'<NewPhonebookURL>(.*)</NewPhonebookURL>', str(response))
                sids = re.findall(r'sid=([0-9a-fA-F]*)', str(response))
                if not len(sids):
                    raise self.LoginFailedException()
                self.__sid = sids[0]
            elif response.status_code == 401:
                raise self.LoginFailedException()
            elif response.status_code == 500:
                raise self.InternalServerErrorException()
            else:
                raise self.RequestFailedException('Request failed with status code: %s' % response.status_code)

        try:
            response = requests.get(phonbook_urls[0], verify=self.__sslverify)
        except socket.error as e:
            raise self.BoxUnreachableException(e)
        except IOError as e:
            raise self.BoxUnreachableException(e)
        except Exception as e:
            raise self.RequestFailedException(e)
        else:
            xml_phonebook = response.content

        return self.__analyzeFritzboxPhonebook(xml_phonebook)

if __name__ == '__main__':

    import sys
    import pprint

    args = {'action':None, 'number':None, 'host':'fritz.box', 'user':None, 'pw':None, 'encrypt':'1', 'id':None, 'imagepath':None}
    try:
        if sys.argv[1]:
            for par in sys.argv[1:]:
                item, value = par.lstrip('-').split('=')
                args[item] = value

            if args['encrypt']:
                args['encrypt'] = True if args['encrypt'].upper() == '1' else False
            box = PytzBox(username=args['user'], password=args['pw'], host=args['host'], encrypt=args['encrypt'], imagepath=args['imagepath'])
            po = pprint.PrettyPrinter(indent=4)
            phone_book_id = 0

            if args['id'] == 'all':
                phone_book_id = -1
            elif args['id'] is not None:
                phone_book_id == args['id']

            if args['action'] == 'getbook':
                po.pprint(box.getPhonebook(id=phone_book_id))
            elif args['action'] == 'getlist':
                po.pprint(box.getPhonebookList())
            elif args['action'] == 'getentry' and args['number']:
                entries = box.getPhonebook(id=phone_book_id)
                for item in entries:
                    for number in entries[item]['numbers']:
                        if box.compareNumbers(args['number'], number):
                            po.pprint(item)
                            po.pprint(entries[item])
    except IndexError:
        print("""
PytzBox

usage:
  ./PytzBox.py --action=getbook --user=<user> --pw=<pass>
              [--host=<fritz.box>] [--id=<int>|all] [--encrypt=0|1]
  ./PytzBox.py --action=getlist --user=<user> --pw=<pass>
              [--host=<fritz.box>] [--encrypt=0|1]
  ./PytzBox.py --action=getentry --number=<number> --user=<user>
               --pw=<pass> [--host=<fritz.box>] [--encrypt=0|1]

options:
  --action=<getbook|getlist>    get all entries of a phonebook
                                get a list of all available phonebooks

  --action=<getentry>           get an entry from a phonebook if number exists
  --number=<number>             search a number in phonebook, in conjunction with --action=getentry

  --user=<user>                 username usually not required
  --pw=<pass>                   admin password [default: none]
  --host=<fritz.box>            ip address / hostname [default: fritz.box]

  --id=<int>|all                use only phonebook with selected id or all
  --encrypt=<0|1>               use SSL encryption [0: No, 1: Yes, default: Yes]

        """)
    except box.BoxUnreachableException(Exception): print('Box unreachable')
    except box.LoginFailedException(Exception): print('Login failed')
    except box.RequestFailedException(Exception): print('Request failed')
    except Exception as e:
        print(e)
