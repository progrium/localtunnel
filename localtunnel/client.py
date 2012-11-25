import argparse
import copy
import json
import uuid

import gevent
from gevent.socket import create_connection

from localtunnel.util import join_sockets, group, recv_json

DEFAULT_BACKEND_PORT = 8001

def client_connector(backend, local_port, tunnel_data):
    try:
        while True:
            init = tunnel_data.pop('init', None)
            backend_client = create_connection(backend)
            if init:
                header = copy.copy(tunnel_data)
                header['new'] = True
            else:
                header = {'name': tunnel_data['name']}
            backend_client.sendall("{0}\n".format(json.dumps(header)))
            header = recv_json(backend_client)
            if header and 'banner' in header:
                print header['banner']
                print "\nPort {0} is now available at http://{1}...".format(
                        local_port, header['host'])
            else:
                local_client = create_connection(('0.0.0.0', local_port))
                join_sockets(backend_client, local_client)
    except AssertionError:
        pass

def run():
    parser = argparse.ArgumentParser(
                description='Open a public HTTP tunnel to a local server')
    parser.add_argument('port', metavar='port', type=int,
                help='local port of server to tunnel to')
    parser.add_argument('-n', dest='name', metavar='name',
                default=str(uuid.uuid4()).split('-')[-1], 
                help='name of the tunnel (default: randomly generate)')
    parser.add_argument('-c', dest='concurrency',
                metavar='concurrency', default=2,
                help='number of concurrent backend connections')
    parser.add_argument('-B', dest='backend', metavar='address',
                default='0.0.0.0', # TODO: change to default public
                help='localtunnel backend hostname (default: localtunnel.com)')
    args = parser.parse_args()

    tunnel_data = {'name': args.name, 'init': True}

    backend = args.backend.split(':')
    if len(backend) == 1:
        backend_address = (backend[0], DEFAULT_BACKEND_PORT)
    else:
        backend_address = (backend[0], int(backend[1]))

    try:
        spawn_args = [client_connector, backend_address, args.port, tunnel_data]
        gevent.joinall(group([
            gevent.spawn(*spawn_args) for n in range(args.concurrency)
        ]))
    except KeyboardInterrupt:
        pass
