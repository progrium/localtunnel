import json
import uuid

import gevent
from gevent.socket import create_connection
from gevent.coros import Semaphore

from gservice.config import Option
from gservice.core import Service

from ws4py.client.geventclient import WebSocketClient

from localtunnel import encode_data_packet
from localtunnel import decode_data_packet

WebSocketClient.upgrade_header = 'X-Upgrade'

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Open a public HTTP tunnel to a local server')
    parser.add_argument('port', metavar='port', type=int,
                       help='local port of server to tunnel to')
    parser.add_argument('--name', dest='name', metavar='name',
                       default=str(uuid.uuid4()).split('-')[-1], 
                       help='name of the tunnel (default: randomly generate)')
    parser.add_argument('--broker', dest='broker', metavar='address',
                       default='localtunnel.com', 
                       help='tunnel broker hostname (default: localtunnel.com)')
    args = parser.parse_args()
    
    client = TunnelClient(args.port, args.name, args.broker)
    client.serve_forever()

class TunnelClient(Service):
    
    def __init__(self, local_port, name, broker_address):
        self.local_port = local_port
        self.ws = WebSocketClient('http://%s/t/%s' % (broker_address, name))
        self.connections = {}
        self.bytes_sent = {}
        self._send_lock = Semaphore()
    
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
                print str(msg)
                conn_id, event = parsed[0:2]
                if event == 'open':
                    self.local_open(conn_id)
                elif event == 'closed':
                    self.local_close(conn_id)
            elif msg.is_binary:
                conn_id, data = decode_data_packet(msg.data)
                self.local_send(conn_id, data)
                
    def local_open(self, conn_id):
        socket = create_connection(('0.0.0.0', self.local_port))
        self.connections[conn_id] = socket
        self.bytes_sent[conn_id] = 0
        gevent.spawn(self.local_recv, conn_id)
    
    def local_close(self, conn_id):
        socket = self.connections.pop(conn_id)
        print "Sent %s" % self.bytes_sent.pop(conn_id)
        try:
            #socket.shutdown(0)
            socket.close()
        except:
            pass
    
    def local_send(self, conn_id, data):
        self.connections[conn_id].send(data)
    
    def local_recv(self, conn_id):
        while True:
            data = self.connections[conn_id].recv(1024)
            if not data:
                break
            self.tunnel_send(conn_id, data)
        self.tunnel_send(conn_id, open=False)
    
    def tunnel_send(self, conn_id, data=None, open=None):
        if open is False:
            msg = [conn_id, 'closed']
            with self._send_lock:
                self.ws.send(json.dumps(msg))
        elif data:
            msg = encode_data_packet(conn_id, data)
            with self._send_lock:
                self.ws.send(msg, binary=True)
            self.bytes_sent[conn_id] += len(data)
        else:
            return