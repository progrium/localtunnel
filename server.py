from twisted.internet import protocol, reactor, defer, task
from twisted.protocols import basic
from twisted.python import log
from twisted.web import http, proxy, resource, server
import sys, time
from urllib import quote as urlquote

import urlparse
import socket
import time

HOSTNAME = 'localtunnel.com'
SSH_USER = 'root'
PORT_RANGE = [9000, 9100]

TUNNELS = {}

def find_port():
    port = PORT_RANGE[0]
    start_time = time.time()
    while not port_available(port):
        if time.time()-start_time > 3:
            raise Exception("No port available")
        port += 1
        if port >= PORT_RANGE[1]: port = PORT_RANGE[0]
    return port

def port_available(port):
    try:
        socket.create_connection(['127.0.0.1', port]).close()
        return False
    except socket.error:
        return True
    

def baseN(num,b=36,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class LocalReverseProxy(proxy.ReverseProxyResource):
    def __init__(self, path='', host='127.0.0.1'):
        proxy.ReverseProxyResource.__init__(self, host, None, path)
    
    def getChild(self, path, request):
        return LocalReverseProxy(self.path + '/' + urlquote(path, safe=""), host=self.host)
    
    def render(self, request):
        tunnel_host = request.getHeader('host').split(':')[0]
        if not tunnel_host in TUNNELS: return "Not found"
        
        request.content.seek(0, 0)
        qs = urlparse.urlparse(request.uri)[4]
        if qs:
            rest = self.path + '?' + qs
        else:
            rest = self.path
        clientFactory = self.proxyClientFactoryClass(
            request.method, rest, request.clientproto,
            request.getAllHeaders(), request.content.read(), request)
        self.reactor.connectTCP(self.host, TUNNELS[tunnel_host], clientFactory)
        return server.NOT_DONE_YET

class TunnelResource(resource.Resource):
    isLeaf = True
    
    def render_GET(self, request):
        port = find_port()
        tunnel_host = '%s.%s' % (baseN(port), HOSTNAME)
        TUNNELS[tunnel_host] = port
        return "ssh -NR %s:localhost:PORT %s@%s\n" % (port, SSH_USER, tunnel_host)
        
log.startLogging(sys.stdout)
reactor.listenTCP(8005, server.Site(LocalReverseProxy()))
reactor.listenTCP(8006, server.Site(TunnelResource()))
reactor.run()