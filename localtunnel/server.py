import argparse
import json
import logging
import re
from socket import MSG_PEEK

import gevent.server

from localtunnel.tunnel import Tunnel
from localtunnel.util import group, join_sockets, recv_json

def backend_handler(socket, address):
    header = recv_json(socket)
    tunnel = Tunnel.get_by_header(header, address[0])
    if not tunnel:
        socket.close()
        return
    if tunnel.new is True:
        tunnel.new = False
        header = {
            "host": "{0}.localtunnel.com".format(tunnel.name), 
            "banner": "Thanks for trying localtunnel v2 beta!"
        }
        socket.sendall("{0}\n".format(json.dumps(header)))
        socket.close()
        logging.debug("tunnel:\"{0}\" created".format(tunnel.name))
    else:
        tunnel.add_backend(socket)
        logging.debug("backend:\"{0}\" added".format(tunnel.name))

def frontend_handler(socket, address):
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
    if not hostname:
        socket.close()
        return
    tunnel = Tunnel.get_by_hostname(hostname)
    if not tunnel:
        socket.close()
        return
    conn = tunnel.pop_backend(wait_timeout=2)
    if not conn:
        socket.close()
        return
    conn.send("\n")
    join_sockets(conn, socket)
    logging.debug("backend:\"{0}\" popped for frontend:\"{1}\"".format(
                tunnel.name, hostname))

        
def run():
    logging.basicConfig(
        format="%(asctime)s %(levelname) 7s %(module)s: %(message)s",
        level='DEBUG')

    parser = argparse.ArgumentParser(description='Localtunnel server daemon')
    parser.add_argument('frontend_port', metavar='frontend_port', type=int,
                help='port to run public frontend', default=8000)
    parser.add_argument('backend_port', metavar='backend_port', type=int,
                help='port to run backend server', default=8001)
    args = parser.parse_args()
    
    logging.info("starting frontend on {0}...".format(args.frontend_port))
    logging.info("starting backend on {0}...".format(args.backend_port))
    
    frontend = gevent.server.StreamServer(
                ('0.0.0.0', args.frontend_port), frontend_handler)
    backend = gevent.server.StreamServer(
                ('0.0.0.0', args.backend_port), backend_handler)
    
    try:
        gevent.joinall(group([
            gevent.spawn(frontend.serve_forever),
            gevent.spawn(backend.serve_forever),
        ]))
    except KeyboardInterrupt:
        pass
