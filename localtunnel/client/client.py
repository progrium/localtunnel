import argparse
import uuid
import sys
import socket

import eventlet
import eventlet.event
import eventlet.greenpool

from localtunnel import util
from localtunnel import protocol
from localtunnel import __version__

def open_proxy_backend(backend, target, name, client):
    proxy = eventlet.connect(backend)
    proxy.sendall(protocol.version)
    protocol.send_message(proxy,
        protocol.proxy_request(
            name=name,
            client=client,
    ))
    reply = protocol.recv_message(proxy)
    if reply and 'proxy' in reply:
        try:
            local = eventlet.connect(target)
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
    parser.add_argument('-m', action='store_true',
                help='show server metrics and exit')


    if '--version' in sys.argv:
        args = parser.parse_args()
        print "client: {}".format(__version__)
        try:
            server_version = util.lookup_server_version(args.host)
        except:
            server_version = '??'
        print "server: {} ({})".format(server_version, args.host)
        sys.exit(0)
    elif '-m' in sys.argv:
        args = parser.parse_args()
        util.print_server_metrics(args.host)
        sys.exit(0)

    parser.add_argument('-n', dest='name', metavar='name',
                default=str(uuid.uuid4()).split('-')[-1],
                help='name of the tunnel (default: randomly generate)')
    parser.add_argument('-c', dest='concurrency', type=int,
                metavar='concurrency', default=3,
                help='number of concurrent backend connections')
    parser.add_argument('target', metavar='target', type=str,
                help='local target port or address of server to tunnel to')
    args = parser.parse_args()


    try:
        backend_port = util.discover_backend_port(args.host)
    except:
        print "  ERROR: Unable to connect to service."
        sys.exit(0)
    frontend_ip = socket.gethostbyname(args.host)
    frontend_address, frontend_hostname = util.parse_address(args.host,
            default_ip=frontend_ip)
    backend = (frontend_address[0], backend_port)

    name = args.name
    client = util.client_name()
    target = util.parse_address(args.target)[0]

    try:
        control = eventlet.connect(backend)
        control.sendall(protocol.version)
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
                            backend, target, name, client)
            proxying = eventlet.spawn(maintain_proxy_backend_pool)

            print "  {0}".format(reply['banner'])
            print "  Port {0} is now accessible from http://{1} ...\n".format(
                    target[1], reply['host'])

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
