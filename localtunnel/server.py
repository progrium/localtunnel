import json
import re
import base64
from socket import MSG_PEEK

import gevent.pywsgi
from gevent.queue import Queue
from gevent.pool import Group
from gevent.socket import create_connection

from gservice.config import Option
from gservice.core import Service

from ws4py.server.geventserver import UpgradableWSGIHandler
from ws4py.client.geventclient import WebSocketClient
from ws4py.server.wsgi.middleware import WebSocketUpgradeMiddleware

def encode_data_packet(conn_id, data):
    return ''.join([chr(conn_id), data])

def decode_data_packet(data):
    return data[0], str(data[1:])

class CodependentGroup(Group):
    """
    A greenlet group that will kill all greenlets if a single one dies.
    """
    def discard(self, greenlet):
        super(CodependentGroup, self).discard(greenlet)
        if not hasattr(self, '_killing'):
            self._killing = True
            gevent.spawn(self.kill)

class TunnelBroker(Service):
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
    
    def open(self, name):
        tunnel = Tunnel()
        self.tunnels[name] = tunnel
        return tunnel
    
    def close(self, name):
        tunnel = self.tunnels.pop(name)
        tunnel.close()
    
    def lookup(self, name):
        return self.tunnels[name]


class BrokerFrontend(gevent.pywsgi.WSGIServer):
    hostname = Option('hostname', default="localtunnel.com")
    
    def __init__(self, broker):
        gevent.pywsgi.WSGIServer.__init__(self, (broker.address, broker.port))
        self.broker = broker
        
    
    def handle(self, socket, address):
        hostname = ''
        hostheader = re.compile('host: ([^\(\);:,<>]+)', re.I)
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
    def __init__(self, socket, hostname, broker):
        self.socket = socket
        self.hostname = hostname
        self.broker = broker

    def handle(self):
        tunnel = self.broker.lookup(self.hostname)
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
            socket.send(data)

class TunnelHandler(UpgradableWSGIHandler):
    def __init__(self, socket, address, broker):
        UpgradableWSGIHandler.__init__(self, socket, address, broker.frontend)
        self.server.application = WebSocketUpgradeMiddleware(
            self.handle_websocket) #, self.handle_http)
        self.broker = broker
    
    def handle_http(self, environ, start_response):
        start_response("200 ok", [])
        return ['<pre>%s' % environ]
    
    def handle_websocket(self, websocket, environ):
        name = environ.get('PATH_INFO', '').split('/')[-1]
        tunnel = self.broker.open(name)
        group = CodependentGroup([
            gevent.spawn(self._tunnel_in, tunnel, websocket),
            gevent.spawn(self._tunnel_out, websocket, tunnel),
        ])
        gevent.joinall(group.greenlets)
        self.broker.close(name)
        websocket.close()
    
    def _tunnel_in(self, tunnel, websocket):
        for type, msg in tunnel:
            if type == 'binary':
                websocket.send(msg, binary=True)
            elif type == 'text':
                websocket.send(msg)
    
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

# XXX: Yeah, obviously this should not live in server.py
class TunnelClient(Service):
    client_port = Option('client_port')
    server_port = Option('port')
    hostname = Option('hostname', default="localtunnel.com")
    
    def __init__(self):
        self.ws = WebSocketClient('http://%s:%s/t/test.localtunnel.local' % 
                    (self.hostname, self.server_port))
        self.connections = {}
    
    def do_start(self):
        self.ws.connect()
        gevent.spawn(self.listen)
        #gevent.spawn(self.visual_heartbeat)
    
    def visual_heartbeat(self):
        while True:
            print "."
            gevent.sleep(1)
    
    def listen(self):
        while True:
            msg = self.ws.receive(msg_obj=True)
            if msg is None:
                print "Trying to stop"
                self.stop()
            if msg.is_text:
                parsed = json.loads(str(msg))
                conn_id, event = parsed[0:2]
                if event == 'open':
                    self.local_open(conn_id)
                elif event == 'closed':
                    self.local_close(conn_id)
            elif msg.is_binary:
                conn_id, data = decode_data_packet(msg.data)
                self.local_send(conn_id, data)
                
    def local_open(self, conn_id):
        socket = create_connection(('127.0.0.1', self.client_port))
        self.connections[conn_id] = socket
        gevent.spawn(self.local_recv, conn_id)
    
    def local_close(self, conn_id):
        socket = self.connections.pop(conn_id)
        try:
            socket.shutdown(0)
            socket.close()
        except:
            pass
    
    def local_send(self, conn_id, data):
        self.connections[conn_id].send(data)
    
    def local_recv(self, conn_id):
        while True:
            data = self.connections[conn_id].recv(4096)
            if not data:
                break
            self.tunnel_send(conn_id, data)
        self.tunnel_send(conn_id, open=False)
    
    def tunnel_send(self, conn_id, data=None, open=None):
        if open is False:
            msg = [conn_id, 'closed']
            self.ws.send(json.dumps(msg))
        elif data:
            msg = encode_data_packet(conn_id, data)
            self.ws.send(msg, binary=True)
        else:
            return