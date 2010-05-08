from twisted.internet import protocol, reactor, defer, task
from twisted.web import http, proxy, resource, server
from twisted.python import log
import sys, time
import urlparse
import socket

SSH_USER = 'localtunnel'
PORT_RANGE = [9000, 9100]

def port_available(port):
    try:
        socket.create_connection(['127.0.0.1', port]).close()
        return False
    except socket.error:
        return True
    
def baseN(num,b=36,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class LocalTunnelReverseProxy(proxy.ReverseProxyResource):
    isLeaf = True
    
    def __init__(self, user, host='127.0.0.1'):
        self.user = user
        self.tunnels = {}
        proxy.ReverseProxyResource.__init__(self, host, None, None)
    
    def find_tunnel_name(self):
        name = baseN(abs(hash(time.time())))[0:3]
        if name in self.tunnels and not port_available(self.tunnels[name]):
            time.sleep(0.1)
            return self.find_tunnel_name()
        return name
        
    def find_tunnel_port(self):
        port = PORT_RANGE[0]
        start_time = time.time()
        while not port_available(port):
            if time.time()-start_time > 3:
                raise Exception("No port available")
            port += 1
            if port >= PORT_RANGE[1]: port = PORT_RANGE[0]
        return port
    
    def garbage_collect(self):
        for name in self.tunnels:
            if port_available(self.tunnels[name]):
                del self.tunnels[name]
    
    def register_tunnel(self, superhost):
        name = self.find_tunnel_name()
        port = self.find_tunnel_port()
        self.tunnels[name] = port
        return "%s:%s@%s.%s" % (port, self.user, name, superhost)
    
    def render(self, request):
        host = request.getHeader('host')
        name, superhost = host.split('.', 1)
        if host.startswith('open.'):
            return self.register_tunnel(superhost)
        else:
            if not name in self.tunnels: return "Not found"
        
            request.content.seek(0, 0)
            clientFactory = self.proxyClientFactoryClass(
                request.method, request.uri, request.clientproto,
                request.getAllHeaders(), request.content.read(), request)
            self.reactor.connectTCP(self.host, self.tunnels[name], clientFactory)
            return server.NOT_DONE_YET

        
log.startLogging(sys.stdout)
reactor.listenTCP(8005, server.Site(LocalTunnelReverseProxy(SSH_USER)))
reactor.run()