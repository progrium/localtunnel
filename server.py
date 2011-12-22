#!/usr/bin/env python
import re
import sys
import socket
import time

import simplejson
from twisted.application import internet
from twisted.python import log
from twisted.web import proxy, server, http
from twisted.web.resource import ErrorPage, NoResource

SSH_OPTIONS = 'command="/bin/echo Shell access denied",no-agent-forwarding,no-pty,no-user-rc,no-X11-forwarding '
KEY_REGEX = re.compile(r'^ssh-(\w{3}) [^\n]+$')
AUTHORIZED_KEYS_FMT = '/home/{}/.ssh/authorized_keys'
BANNER = "This localtunnel service is brought to you by {}."
PORT_RANGE = [32000, 64000]

def port_available(port):
    try:
        socket.create_connection(['127.0.0.1', port]).close()
        return False
    except socket.error:
        return True

def baseN(num, b=32, numerals="23456789abcdefghijkmnpqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class LocalTunnelReverseProxy(proxy.ReverseProxyResource):
    isLeaf = True
    
    def __init__(self, user, host_name, address, provider, strip_subdomain=True, auth=None):
        self.user = user
        self.host_name = host_name
        self.host_sub_name = self.host_name.split('.')[0]
        self.authorized_keys = AUTHORIZED_KEYS_FMT.format(self.user)
        self.tunnels = {}
        self.banner = BANNER.format(provider)
        self.strip_subdomain = strip_subdomain
        self.auth = auth 
        proxy.ReverseProxyResource.__init__(self, address, None, None)
    
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
            if port >= PORT_RANGE[1]:
                port = PORT_RANGE[0]
        return port
    
    def garbage_collect(self):
        for name in self.tunnels:
            if port_available(self.tunnels[name]):
                del self.tunnels[name]
    
    def install_key(self, key):
        if not KEY_REGEX.match(key.strip()):
            return False
        key = ''.join([SSH_OPTIONS, key.strip(), "\n"])
        fr = open(self.authorized_keys, 'r')
        if not key in fr.readlines():
            fa = open(self.authorized_keys, 'a')
            fa.write(key)
            fa.close()
        fr.close()
        return True
    
    def register_tunnel(self, superhost, key=None):
        if key and not self.install_key(key):
            return simplejson.dumps(dict(error="Invalid key."))
        name = self.find_tunnel_name()
        port = self.find_tunnel_port()
        self.tunnels[name] = port
        return simplejson.dumps(
            dict(through_port=port,
                 user=self.user, host='%s.%s' % (name, superhost),
                 banner=self.banner))
    
    def render(self, request):        
        host = request.getHeader('host')
        if self.strip_subdomain:
            parts = host.split('.', 1)
            name, superhost = ('', host) if len(parts) == 1 else parts
        else:
            parts = host.split('.', 1)
            name = '' if len(parts) == 1 else parts[0] 
            superhost = host
        if host.startswith(self.host_sub_name):
            if self.auth:
                user = request.getUser()
                password = request.getPassword()
                if not user or not password or not self.auth(user, password):
                    request.setHeader('WWW-Authenticate', 'Basic realm="www"')
                    page = ErrorPage(http.UNAUTHORIZED, 'Authorization Required', '')
                    return page.render(request)
            request.setHeader('Content-Type', 'application/json')
            return self.register_tunnel(superhost, request.args.get('key', [None])[0])
        else:
            if not name in self.tunnels:
                return NoResource().render(request)
            request.content.seek(0, 0)
            clientFactory = self.proxyClientFactoryClass(
                request.method,
                request.uri,
                request.clientproto,
                request.getAllHeaders(),
                request.content.read(),
                request)
            self.reactor.connectTCP(self.host, self.tunnels[name], clientFactory)
            return server.NOT_DONE_YET

def getWebService(user, host_name, address, port, provider, strip_subdomain, auth):
    proxySite = server.Site(LocalTunnelReverseProxy(
        user,
        host_name,
        address,
        provider,
        strip_subdomain,
        auth))
    return internet.TCPServer(port, proxySite)

if __name__ == '__main__':
    import getpass
    
    from twisted.internet import reactor
    
    log.startLogging(sys.stdout)
    proxyServer = server.Site(LocalTunnelReverseProxy(
        user=getpass.getuser(),
        host_name='localtunnel.noone.com',
        address='127.0.0.1',
        provider='noone',
        strip_subdomain=True))
    reactor.listenTCP(8080, proxyServer)
    reactor.run()
