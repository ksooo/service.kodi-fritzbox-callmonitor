__author__ = 'Frank Epperlein'
__doc__ = """
SimpleGdataRequest.py

Usage:
    SimpleGdataRequest.py listcontacts --username=<user> --password=<pass>
    SimpleGdataRequest.py get <url> --username=<user> --password=<pass> --service=<service>
"""

import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import socket
import xml.dom.minidom

class SimpleGdataRequest(object):
    class AuthorizationTokenRequestException(Exception):
        pass

    class AuthorizationMethodInvalidException(Exception):
        pass

    class NotAuthorizedException(Exception):
        pass

    class RequestFailedException(Exception):
        pass

    def __init__(self, authorization_token=False):
        self.__authorization_token = authorization_token

    def get_authorization_token(self):
        if self.__authorization_token:
            return self.__authorization_token
        else:
            raise self.NotAuthorizedException()

    def authorize(self, username, password, service, method='ClientLogin', source='SimpleGdataRequest',
                  account_type='HOSTED_OR_GOOGLE'):
        """
        request an google api authorization token

        :param username: user login name
        :param password: user login password
        :param method: one of ['ClientLogin', 'OAuth 2.0']
                       currently ClientLogin is the only valid option, which is valid until April 20, 2015

        for ClientLogin:
        :param service:  service names from https://developers.google.com/gdata/faq?hl=de&csw=1#clientlogin
        :param account_type: account types from https://developers.google.com/accounts/docs/AuthForInstalledApps
        :param source: simple string to identify request
        """

        self.__authorization_token = False

        if method == 'ClientLogin':
            request = urllib.request.urlopen(
                'https://www.google.com/accounts/ClientLogin',
                urllib.parse.urlencode(dict(
                    Email=username,
                    Passwd=password,
                    accountType=account_type,
                    source=source,
                    service=service
                )))

            for line in request.readlines():
                key, value = line.split('=')

                if key == 'Error':
                    raise self.AuthorizationTokenRequestException(value)

                if key == 'Auth':
                    self.__authorization_token = value.strip()
                    return True
        else:
            raise self.AuthorizationMethodInvalidException(method)

    def request(self, url, data=None, headers=False, timeout=30, pretty=True):

        if not isinstance(headers, dict):
            headers = dict()
        headers['Authorization'] = "GoogleLogin Auth=%s" % self.get_authorization_token()

        request = urllib.request.Request(url, data, headers=headers)

        try:
            response = urllib.request.urlopen(request, timeout=timeout)
        except socket as e:
            raise self.RequestFailedException(str(e))
        except IOError as e:
            raise self.RequestFailedException(str(e))
        except Exception as e:
            raise self.RequestFailedException(str(e))
        else:
            result = response.read()
            if pretty:
                if result.startswith('<?xml'):
                    xml_dom = xml.dom.minidom.parseString(result)
                    return xml_dom.toprettyxml()
            return result


if __name__ == '__main__':

    import docopt

    arguments = docopt.docopt(__doc__)
    gd = SimpleGdataRequest()

    if arguments['listcontacts']:
        gd.authorize(arguments['--username'], arguments['--password'], 'cp')
        print(gd.request('https://www.google.com/m8/feeds/contacts/%s/full' % arguments['--username']))
    elif arguments['get']:
        gd.authorize(arguments['--username'], arguments['--password'], arguments['--service'])
        print(gd.request(arguments['<url>']))