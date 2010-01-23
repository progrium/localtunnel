from twisted.internet import protocol, reactor, defer, task
from twisted.protocols import basic
from twisted.python import log
from twisted.web import http
import sys, time

# Debug thing
FIXED_TUNNEL_NAME = True

tunnels = {}

def baseN(num,b=36,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class IncomingChannel(basic.LineReceiver):
    tunnel = None
    buffer = []
    
    def lineReceived(self, line):
        if not self.tunnel:
            self.buffer.append(line)
            if line.lower().startswith("host: "):
                host = line.lower().split(': ')[1]
                if host in tunnels:
                    self.tunnel = tunnels[host]
                    self.tunnel.incoming = self
                    for l in self.buffer:
                        self.tunnel.send(l + '\r\n')
                else:
                    self.transport.loseConnection()
        else:
            self.tunnel.send(line + '\r\n')
    
    def rawDataReceived(self, data):
        self.tunnel.send(data)
    
    def connectionMade(self):
        self.reqId = hash(time.time())
        self.buffer = ['^^CONNECT--']
    
    def connectionLost(self, reason):
        if self.tunnel:
            self.tunnel.send('^^CLOSE--\r\n')


class IncomingFactory(protocol.ServerFactory):
    protocol = IncomingChannel

class TunnelServerProtocol(protocol.Protocol):
    incoming = None
    
    def dataReceived(self, data):
        self.incoming.transport.write(data)

    def connectionMade(self):
        host = 'localhost:8999' if FIXED_TUNNEL_NAME else '%s.localhost:8999' % baseN(abs(hash(time.time())))
        print "!!! Use hostname %s !!!" % host
        tunnels[host] = self
        
    def send(self, data):
        self.transport.write('%s|%s' % (self.incoming.reqId, data))
        

class TunnelServerFactory(protocol.ServerFactory):
    protocol = TunnelServerProtocol

log.startLogging(sys.stdout)
reactor.listenTCP(8777, TunnelServerFactory())
reactor.listenTCP(8999, IncomingFactory())
reactor.run()