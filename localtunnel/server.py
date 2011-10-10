import json
import re
import base64
from socket import MSG_PEEK

import gevent.pywsgi
from gevent.queue import Queue
from gevent.pool import Group

from gservice.config import Option
from gservice.core import Service

from ws4py.server.geventserver import UpgradableWSGIHandler
from ws4py.server.wsgi.middleware import WebSocketUpgradeMiddleware

from localtunnel import encode_data_packet
from localtunnel import decode_data_packet

UpgradableWSGIHandler.upgrade_header = 'X-Upgrade'

class CodependentGroup(Group):
    """Greenlet group that will kill all greenlets if a single one dies
    """
    def discard(self, greenlet):
        super(CodependentGroup, self).discard(greenlet)
        if not hasattr(self, '_killing'):
            self._killing = True
            gevent.spawn(self.kill)

class TunnelBroker(Service):
    """Top-level service that manages tunnels and runs the frontend"""
    
    port = Option('port', default=80)
    address = Option('address', default='0.0.0.0')
    
    def __init__(self):
        self.frontend = BrokerFrontend(self)
        self.add_service(self.frontend)
        
        self.tunnels = {}
    
    #def do_start(self):
    #    gevent.spawn(self.visual_heartbeat)
    
    def visual_heartbeat(self):
        while True:
            print "."
            gevent.sleep(1)
    
    def open_tunnel(self, name):
        tunnel = Tunnel()
        self.tunnels[name] = tunnel
        return tunnel
    
    def close_tunnel(self, name):
        tunnel = self.tunnels.pop(name)
        tunnel.close()
    
    def lookup_tunnel(self, name):
        return self.tunnels.get(name)


class BrokerFrontend(gevent.pywsgi.WSGIServer):
    """Server that will manage a tunnel or proxy traffic through a tunnel"""
    
    hostname = Option('hostname', default="localtunnel.com")
    
    def __init__(self, broker):
        gevent.pywsgi.WSGIServer.__init__(self, (broker.address, broker.port))
        self.broker = broker
        
    
    def handle(self, socket, address):
        hostname = ''
        hostheader = re.compile('host: ([^\(\);:,<>]+)', re.I)
        # Peek up to 512 bytes into data for the Host header
        for n in [128, 256, 512]:
            bytes = socket.recv(n, MSG_PEEK)
            if not bytes:
                break
            for line in bytes.split('\r\n'):
                match = hostheader.match(line)
                if match:
                    hostname = match.group(1)
            if hostname:
                break
        hostname = hostname.split(':')[0]
        if hostname.endswith('.%s' % self.hostname):
            handler = ProxyHandler(socket, hostname, self.broker)
            handler.handle()
        else:
            handler = TunnelHandler(socket, address, self.broker)
            handler.handle()

class ProxyHandler(object):
    """TCP-ish proxy handler"""
    
    def __init__(self, socket, hostname, broker):
        self.socket = socket
        self.hostname = hostname
        self.broker = broker

    def handle(self):
        tunnel = self.broker.lookup_tunnel(self.hostname.split('.')[0])
        if tunnel:
            conn = tunnel.create_connection()
            group = CodependentGroup([
                gevent.spawn(self._proxy_in, self.socket, conn),
                gevent.spawn(self._proxy_out, conn, self.socket),
            ])
            gevent.joinall(group.greenlets)
        try:
            self.socket.shutdown(0)
            self.socket.close()
        except:
            pass
    
    def _proxy_in(self, socket, conn):
        while True:
            data = socket.recv(2048)
            if not data:
                return
            conn.send(data)
    
    def _proxy_out(self, conn, socket):
        while True:
            data = conn.recv()
            if data is None:
                return
            socket.sendall(data)
            

class TunnelHandler(UpgradableWSGIHandler):
    """HTTP handler for opening/managing/running a tunnel (via websocket)"""
    
    def __init__(self, socket, address, broker):
        UpgradableWSGIHandler.__init__(self, socket, address, broker.frontend)
        self.server.application = WebSocketUpgradeMiddleware(
            self.handle_websocket, self.handle_http)
        self.broker = broker
    
    def handle_http(self, environ, start_response):
        start_response("200 ok", [])
        return ['<pre>%s' % environ]
    
    def handle_websocket(self, websocket, environ):
        name = environ.get('PATH_INFO', '').split('/')[-1]
        tunnel = self.broker.open_tunnel(name)
        group = CodependentGroup([
            gevent.spawn(self._tunnel_in, tunnel, websocket),
            gevent.spawn(self._tunnel_out, websocket, tunnel),
        ])
        gevent.joinall(group.greenlets)
        self.broker.close_tunnel(name)
        websocket.close()
    
    def _tunnel_in(self, tunnel, websocket):
        for type, msg in tunnel:
            binary = bool(type == 'binary')
            websocket.send(msg, binary=binary)
    
    def _tunnel_out(self, websocket, tunnel):
        while True:
            msg = websocket.receive(msg_obj=True)
            if msg is None:
                return
            if msg.is_text:
                tunnel.dispatch(message=str(msg))
            elif msg.is_binary:
                tunnel.dispatch(data=msg.data)

class Tunnel(object):
    """Server representation of a tunnel its mux'd connections"""
    def __init__(self):
        self.connections = {}
        self.tunnelq = Queue()
    
    def create_connection(self):
        id = 0
        while id in self.connections.keys():
            id += 1
            id %= 2**31
        conn = ConnectionProxy(id, self)
        self.connections[id] = conn
        return conn
    
    def close(self):
        for conn_id in self.connections:
            conn = self.connections.pop(conn_id)
            conn.close()
    
    def __iter__(self):
        return self
    
    def next(self):
        return self.tunnelq.get()
    
    def dispatch(self, message=None, data=None):
        """ From the tunnel (server) to the proxy (client) """
        if message:
            try:
                parsed = json.loads(message)
            except ValueError:
                raise
            conn_id, event = parsed[0:2]
            if conn_id not in self.connections:
                return
            if event == 'closed':
                conn = self.connections.pop(conn_id)
                conn.close()
        elif data:
            conn_id, data = decode_data_packet(data)
            self.connections[conn_id].recvq.put(data)

class ConnectionProxy(object):
    """Socket-like representation of connection on the other end of the tunnel
    """
    
    def __init__(self, id, tunnel):
        self.tunnel = tunnel
        self.id = id
        self.recvq = Queue()
        self.send(open=True)
    
    def recv(self):
        return self.recvq.get()
    
    def send(self, data=None, open=None):
        """ From the proxy (client) to the tunnel (server) """
        if open is True:
            msg = [self.id, 'open']
            self.tunnel.tunnelq.put(('text', json.dumps(msg)))
        elif open is False:
            msg = [self.id, 'closed']
            self.tunnel.tunnelq.put(('text', json.dumps(msg)))
        else:
            data = encode_data_packet(self.id, data)
            self.tunnel.tunnelq.put(('binary', data))
        
    def close(self):
        self.recvq.put(None)
        self.send(open=False)

