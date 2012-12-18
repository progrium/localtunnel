import argparse
import json
import logging
import re
import os
from socket import MSG_PEEK

import eventlet
import eventlet.debug
import eventlet.greenpool
from eventlet.timeout import Timeout

from localtunnel.tunnel import Tunnel
from localtunnel import util
from localtunnel import protocol
from localtunnel import VERSION

HOST_TEMPLATE = "{0}.v2.localtunnel.com"
BANNER = """Thanks for trying localtunnel v2 beta!
  Source code: https://github.com/progrium/localtunnel
  Donate: http://j.mp/donate-localtunnel
"""
HEARTBEAT_INTERVAL = 5

def backend_handler(socket, address):
    try:
        protocol.assert_protocol(socket)
        message = protocol.recv_message(socket)
        if message and 'control' in message:
            handle_control(socket, message['control'])
        elif message and 'proxy' in message:
            handle_proxy(socket, message['proxy'])
        else:
            logging.debug("!backend: no request message, closing")
    except AssertionError:
        logging.debug("!backend: invalid protocol, closing")
    
def handle_control(socket, request):
    try:
        tunnel = Tunnel.get_by_control_request(request)
    except RuntimeError, e:
        protocol.send_message(socket, error_reply('notavailable'))
        socket.close()
        return
    protocol.send_message(socket, protocol.control_reply(
        host=HOST_TEMPLATE.format(tunnel.name),
        banner=BANNER,
        concurrency=Tunnel.max_pool_size,
    ))
    logging.info("created tunnel:\"{0}\" by client:\"{1}\"".format(
            tunnel.name, tunnel.client))

    try:
        while True:
            eventlet.sleep(HEARTBEAT_INTERVAL)
            protocol.send_message(socket, protocol.control_ping())
            with Timeout(HEARTBEAT_INTERVAL):
                message = protocol.recv_message(socket)
                assert message == protocol.control_pong()
    except (IOError, AssertionError, Timeout):
        logging.debug("expiring tunnel:\"{0}\"".format(tunnel.name))
        tunnel.destroy()

def handle_proxy(socket, request):
    try:
        tunnel = Tunnel.get_by_proxy_request(request)
    except RuntimeError, e:
        protocol.send_message(socket, protocol.error_reply('notavailable'))
        socket.close()
        return
    if not tunnel:
        protocol.send_message(socket, protocol.error_reply('expired'))
        socket.close()
        return
    try:
        tunnel.add_proxy_backend(socket)
        logging.debug("added backend:\"{0}\" by client:\"{1}\"".format(
            tunnel.name, tunnel.client))
        util.leave_socket_open()
    except ValueError, e:
        logging.debug(str(e))

def frontend_handler(socket, address):
    hostname = ''
    hostheader = re.compile('host: ([^\(\);:,<>]+)', re.I)
    # Peek up to 512 bytes into data for the Host header
    for n in [128, 256, 512]:
        bytes = socket.recv(n, MSG_PEEK)
        if not bytes:
            socket.close()
            return
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
    if hostname.startswith('_version.'):
        data = """HTTP/1.1 200 OK\r\nContent-Length: {0}\r\nConnection: close\r\n\r\n{1}
               """.format(len(VERSION), VERSION).strip()
        socket.sendall(data)
        socket.close()
        return
    if hostname.startswith('_backend.'):
        port = os.environ.get('DOTCLOUD_SERVER_BACKEND_PORT', Tunnel.backend_port)
        data = """HTTP/1.1 200 OK\r\nContent-Length: {0}\r\nConnection: close\r\n\r\n{1}
               """.format(len(str(port)), port).strip()
        socket.sendall(data)
        socket.close()
        return
    tunnel = Tunnel.get_by_hostname(hostname)
    if not tunnel:
        logging.debug("!frontend: no tunnel, closing ({0})".format(
            hostname))
        socket.close()
        return
    conn = tunnel.pop_proxy_backend(timeout=2)
    if not conn:
        logging.debug("!frontend: no backend, closing")
        socket.close()
        return
    protocol.send_message(conn, protocol.proxy_reply())
    pool = util.join_sockets(conn, socket)
    logging.debug("popped backend:\"{0}\" for frontend:\"{1}\"".format(
                tunnel.name, hostname))
    pool.waitall()

        
def run():
    eventlet.debug.hub_prevent_multiple_readers(False)
    eventlet.monkey_patch(socket=True)

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
    
    Tunnel.backend_port = args.backend_port
    
    if args.domainpart:
        Tunnel.domain_part = args.domainpart
    
    stats_key = os.environ.get('STATHAT_EZKEY', None)
    if stats_key:
        Tunnel.stats = util.StatHat(stats_key, 'localtunnel.')
        logging.info("starting stats session with {0}".format(stats_key))

    frontend_listener = eventlet.listen(('0.0.0.0', args.frontend_port))
    backend_listener = eventlet.listen(('0.0.0.0', args.backend_port))
    
    try:
        Tunnel.schedule_idle_scan()
        pool = eventlet.greenpool.GreenPool(size=2)
        pool.spawn_n(eventlet.serve, frontend_listener, frontend_handler)
        pool.spawn_n(eventlet.serve, backend_listener, backend_handler)
        pool.waitall()
    except KeyboardInterrupt:
        pass
