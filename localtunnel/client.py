import argparse
import copy
import json
import uuid
import sys

import gevent
import gevent.event
from gevent.socket import create_connection

from localtunnel.util import join_sockets
from localtunnel.util import group
from localtunnel.util import recv_json
from localtunnel.util import client_name
from localtunnel.util import discover_backend_port

def client_connector(backend, local_port, tunnel_data,
            ready=gevent.event.Event()):
    while True:
        init = tunnel_data.pop('init', None)
        header = copy.copy(tunnel_data)
        if init:
            header['new'] = True
            ready.clear()
        elif not ready.isSet():
            ready.wait()
        backend_client = create_connection(backend)
        backend_client.sendall("{0}\n".format(json.dumps(header)))
        header = recv_json(backend_client)
        if header and 'banner' in header:
            print "  {0}".format(header['banner'])
            print "  Port {0} is now accessible from http://{1} ...\n".format(
                    local_port, header['host'])
            ready.set()
        elif header and 'error' in header:
            print "  ERROR: {0}".format(header['error'])
            gevent.hub.get_hub().parent.throw(SystemExit(1))
        else:
            local_client = create_connection(('0.0.0.0', local_port))
            join_sockets(backend_client, local_client)

def run():
    parser = argparse.ArgumentParser(
                description='Open a public HTTP tunnel to a local server')
    parser.add_argument('port', metavar='port', type=int,
                help='local port of server to tunnel to')
    parser.add_argument('-n', dest='name', metavar='name',
                default=str(uuid.uuid4()).split('-')[-1], 
                help='name of the tunnel (default: randomly generate)')
    parser.add_argument('-c', dest='concurrency', type=int,
                metavar='concurrency', default=3,
                help='number of concurrent backend connections')
    parser.add_argument('-s', dest='host', metavar='address',
                default='v2.localtunnel.com',
                help='localtunnel server address (default: v2.localtunnel.com)')
    args = parser.parse_args()

    tunnel_data = {
            'name': args.name, 
            'client': client_name(),
            'init': True,
    }

    host = args.host.split(':')
    if len(host) == 1:
        backend_address = (host[0], discover_backend_port(host[0]))
    else:
        backend_address = (host[0], discover_backend_port(host[0], int(host[1])))

    try:
        spawn_args = [client_connector, backend_address, args.port, tunnel_data]
        gevent.joinall(group([
            gevent.spawn(*spawn_args) for n in range(args.concurrency)
        ]))
    except KeyboardInterrupt:
        pass
