from twisted.internet import protocol, reactor, defer, task
from twisted.web import http, proxy, resource, server
from twisted.python import log
import sys, time
import urlparse
import socket
import simplejson
import re

SSH_USER = 'localtunnel'
AUTHORIZED_KEYS = '/home/localtunnel/.ssh/authorized_keys'
PORT_RANGE = [32000, 64000]
BANNER = "This localtunnel service is brought to you by Twilio."

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
        name = baseN(abs(hash(time.time())))[0:4]
        if (name in self.tunnels and not port_available(self.tunnels[name])) or name == 'open':
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
    
    def install_key(self, key):
        key = key.strip()+"\n"
        f = open(AUTHORIZED_KEYS, 'ra')
        if not key in f.readlines():
            f.write(key)
        f.close()
    
    def register_tunnel(self, superhost, key=None):
        if key: self.install_key(key)
        name = self.find_tunnel_name()
        port = self.find_tunnel_port()
        self.tunnels[name] = port
        return simplejson.dumps(
            dict(through_port=port, user=self.user, host='%s.%s' % (name, superhost), banner=BANNER))
    
    def render(self, request):
        host = request.getHeader('host')
        name, superhost = host.split('.', 1)
        if host.startswith('open.'):
            request.setHeader('Content-Type', 'application/json')
            return self.register_tunnel(superhost, request.args.get('key', [None])[0])
        else:
            if not name in self.tunnels: return "Not found"
        
            request.content.seek(0, 0)
            clientFactory = self.proxyClientFactoryClass(
                request.method, request.uri, request.clientproto,
                request.getAllHeaders(), request.content.read(), request)
            self.reactor.connectTCP(self.host, self.tunnels[name], clientFactory)
            return server.NOT_DONE_YET

#if 'location' in request.responseHeaders and host in request.responseHeaders['location']:
#    # Strip out the port they think they need
#    p = re.compile(r'%s\:\d+' % host)
#    location = p.sub(host, request.responseHeaders['location'])
#    request.responseHeaders['location'] = location

        
log.startLogging(sys.stdout)
reactor.listenTCP(80, server.Site(LocalTunnelReverseProxy(SSH_USER)))
reactor.run()