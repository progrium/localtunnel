from twisted.internet import protocol, reactor, defer, task
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.protocols import basic
from twisted.python import log
from twisted.web import http
import sys

class OutgoingChannel(protocol.Protocol):
    def __init__(self, reqId, factory):
        self.reqId = reqId
        self.factory = factory
        self.tunnel = factory.tunnel
    
    def dataReceived(self, data):
        self.tunnel.transport.write(data)
    
    def connectionMade(self):
        self.tunnel.requests[self.reqId] = self
        for l in self.tunnel.buffers[self.reqId]:
            self.transport.write(l + "\r\n")
    
class OutgoingFactory(ClientFactory):
    def __init__(self, reqId, tunnel):
        self.reqId = reqId
        self.tunnel = tunnel
    
    def buildProtocol(self, addr):
        self.p = OutgoingChannel(self.reqId, self)
        return self.p

class TunnelClientProtocol(basic.LineReceiver):
    requests = {}
    buffers = {}
    
    def lineReceived(self, line):
        reqId, line = line.split('|',1)
        if not reqId in self.requests:
            if line == '^^CONNECT--':
                self.buffers[reqId] = []
                reactor.connectTCP("localhost", self.factory.port, OutgoingFactory(reqId, self))
            else:
                self.buffers[reqId].append(line)
        else:
            if line == '^^CLOSE--':
                if reqId in self.requests and self.requests[reqId]:
                    self.requests[reqId].transport.loseConnection()
                self.requests[reqId] = None
            else:
                self.requests[reqId].transport.write(line + "\r\n")
                
    def rawDataReceived(self, data):
        print "HUH?", data
        
    def connectionMade(self):
        print "Listening on port %s. See server for host information." % self.factory.port

class TunnelClientFactory(ClientFactory):
    protocol = TunnelClientProtocol
    
    def __init__(self, port):
        self.port = port

#log.startLogging(sys.stdout)
try:
    reactor.connectTCP("localhost", 8777, TunnelClientFactory(int(sys.argv[1])))
    reactor.run()
except IndexError:
    print "Usage: %s <port>" % sys.argv[0]
    print "  You need to specify a port to forward to."