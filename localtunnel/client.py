import argparse
import uuid
import sys

import eventlet
import eventlet.event
import eventlet.greenpool

from localtunnel import util
from localtunnel import protocol
from localtunnel import VERSION

def open_proxy_backend(backend, port, name, client):
    proxy = eventlet.connect(backend)
    proxy.sendall(protocol.VERSION)
    protocol.send_message(proxy, 
        protocol.proxy_request(
            name=name, 
            client=client,
    ))
    reply = protocol.recv_message(proxy)
    if reply and 'proxy' in reply:
        try:
            local = eventlet.connect(('0.0.0.0', port))
            util.join_sockets(proxy, local)
        except IOError:
            proxy.close()
    elif reply and 'error' in reply:
        print "  ERROR: {0}".format(reply['error'])
        return
    else:
        pass
 
def run():
    parser = argparse.ArgumentParser(
                description='Open a public HTTP tunnel to a local server')
    parser.add_argument('-s', dest='host', metavar='address',
                default='v2.localtunnel.com',
                help='localtunnel server address (default: v2.localtunnel.com)')
    parser.add_argument('--version', action='store_true',
                help='show version information for client and server')
    
    if '--version' in sys.argv:
        args = parser.parse_args()
        try:
            server_version = util.lookup_server_version(args.host)
        except:
            server_version = '??'
        print "client: {}".format(VERSION)
        print "server: {} ({})".format(server_version, args.host)
        sys.exit(0)
    
    parser.add_argument('-n', dest='name', metavar='name',
                default=str(uuid.uuid4()).split('-')[-1], 
                help='name of the tunnel (default: randomly generate)')
    parser.add_argument('-c', dest='concurrency', type=int,
                metavar='concurrency', default=3,
                help='number of concurrent backend connections')
    parser.add_argument('port', metavar='port', type=int,
                help='local port of server to tunnel to')
    args = parser.parse_args()
        
    host = args.host.split(':')
    if len(host) == 1:
        backend_port = util.discover_backend_port(host[0])
    else:
        backend_port = util.discover_backend_port(host[0], int(host[1]))
    backend = (host[0], backend_port)

    name = args.name
    client = util.client_name()
    port = args.port

    try:
        control = eventlet.connect(backend)
        control.sendall(protocol.VERSION)
        protocol.send_message(control, 
            protocol.control_request(
                name=name, 
                client=client,
        ))
        reply = protocol.recv_message(control)
        if reply and 'control' in reply:
            reply = reply['control']

            def maintain_proxy_backend_pool():
                pool = eventlet.greenpool.GreenPool(reply['concurrency'])
                while True:
                    pool.spawn_n(open_proxy_backend, 
                            backend, port, name, client)
            proxying = eventlet.spawn(maintain_proxy_backend_pool)

            print "  {0}".format(reply['banner'])
            print "  Port {0} is now accessible from http://{1} ...\n".format(
                    port, reply['host'])

            try:
                while True:
                    message = protocol.recv_message(control)
                    assert message == protocol.control_ping()
                    protocol.send_message(control, protocol.control_pong())
            except (IOError, AssertionError):
                proxying.kill()
            
        elif reply and 'error' in reply:
            print "  ERROR: {0}".format(reply['message'])
        else:
            print "  ERROR: Unexpected server reply."
            print "         Make sure you have the latest version of the client."
    except KeyboardInterrupt:
        pass
