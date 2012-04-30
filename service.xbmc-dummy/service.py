import asyncore, socket, xbmc

class FritzClient(asyncore.dispatcher):

    def __init__(self, host,port):
        asyncore.dispatcher.__init__(self)
        xbmc.log('DUMMY FritzClientMeldetSich')
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (host, port) )

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        antwort = self.recv(1024) 
        log= "[%s] %s" % ('192.168.178.1',antwort)
        xbmc.log(log)

    def writable(self):
        pass

    def handle_write(self):
        pass



