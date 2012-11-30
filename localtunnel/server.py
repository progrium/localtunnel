import argparse
import json
import logging
import re
import os
from socket import MSG_PEEK

import gevent.server

from localtunnel.tunnel import Tunnel
from localtunnel.util import group, join_sockets, recv_json

HOST_TEMPLATE = "{0}.v2.localtunnel.com"
BANNER = "Thanks for trying localtunnel v2 beta!"

def backend_handler(socket, address):
    header = recv_json(socket)
    if not header:
        logging.debug("!backend: no header, closing")
        socket.close()
        return
    tunnel = Tunnel.get_by_header(header)
    if not tunnel:
        logging.debug("!backend: no tunnel, closing")
        socket.close()
        return
    if tunnel.new is True:
        tunnel.new = False
        header = {
            "host": HOST_TEMPLATE.format(tunnel.name), 
            "banner": BANNER
        }
        socket.sendall("{0}\n".format(json.dumps(header)))
        socket.close()
        logging.info("created tunnel:\"{0}\" by client:\"{1}\"".format(
            tunnel.name, tunnel.client))
    else:
        try:
            tunnel.add_backend(socket)
            logging.debug("added backend:\"{0}\" by client:\"{1}\"".format(
                    tunnel.name, tunnel.client))
        except ValueError, e:
            logging.debug(str(e))

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
        logging.debug("!frontend: no hostname, closing")
        socket.close()
        return
    if hostname.startswith('_backend.'):
        socket.send(
            "{0}\n".format(os.environ.get(
                'DOTCLOUD_SERVER_BACKEND_PORT', Tunnel.backend_port)))
        socket.close()
        return
    tunnel = Tunnel.get_by_hostname(hostname)
    if not tunnel:
        logging.debug("!frontend: no tunnel, closing")
        socket.close()
        return
    conn = tunnel.pop_backend(timeout=2)
    if not conn:
        logging.debug("!frontend: no backend, closing")
        socket.close()
        return
    conn.send("\n")
    join_sockets(conn, socket)
    logging.debug("popped backend:\"{0}\" for frontend:\"{1}\"".format(
                tunnel.name, hostname))

        
def run():
    logging.basicConfig(
        format="%(asctime)s %(levelname) 7s %(module)s: %(message)s",
        level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Localtunnel server daemon')
    parser.add_argument('frontend_port', metavar='frontend_port', type=int,
                help='port to run public frontend', default=8000)
    parser.add_argument('backend_port', metavar='backend_port', type=int,
                help='port to run backend server', default=8001)
    parser.add_argument('-d', '--domainpart', type=int,
                help='domain part (from the right) to extract tunnel name')
    args = parser.parse_args()
    
    logging.info("starting frontend on {0}...".format(args.frontend_port))
    logging.info("starting backend on {0}...".format(args.backend_port))
    
    if args.domainpart:
        Tunnel.domain_part = args.domainpart
    Tunnel.backend_port = args.backend_port

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
