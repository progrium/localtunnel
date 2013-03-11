import json
import logging
import re
import os
from socket import MSG_PEEK

from localtunnel.server.tunnel import Tunnel
from localtunnel import util
from localtunnel import protocol
from localtunnel import __version__
from localtunnel.server import metrics

def peek_http_host(socket):
    host = ''
    hostheader = re.compile('host: ([^\(\);:,<>]+)', re.I)
    # Peek up to 2048 bytes into data for the Host header
    for n in [128, 256, 512, 1024, 2048]:
        bytes = socket.recv(n, MSG_PEEK)
        if not bytes:
            break
        for line in bytes.split('\r\n'):
            match = hostheader.match(line)
            if match:
                host = match.group(1)
        if host:
            break
    return host

def send_http_response(socket, content):
    data =  """HTTP/1.1 200 OK\r\nContent-Length: {0}\r\nConnection: close\r\n\r\n{1}
            """.format(len(str(content)), content).strip()
    socket.sendall(data)


@metrics.time_calls(name='frontend_conn')
def connection_handler(socket, address):
    host = peek_http_host(socket)
    hostname = host.split(':')[0]
    if not hostname:
        logging.debug("!no hostname, closing")
        socket.close()
        return

    if hostname.startswith('_version.'):
        send_http_response(socket, __version__)
        socket.close()
        logging.debug("version request from {0}".format(address[0]))
        return

    if hostname.startswith('_backend.'):
        port = os.environ.get('DOTCLOUD_SERVER_BACKEND_PORT', 
                    Tunnel.backend_port)
        send_http_response(socket, port)
        socket.close()
        return

    if hostname.startswith('_metrics.'):
        content = json.dumps(metrics.dump_metrics(),
                    sort_keys=True, indent=2, separators=(',', ': '))
        send_http_response(socket, content)
        socket.close()
        logging.debug("metrics request from {0}".format(address[0]))
        return

    tunnel = Tunnel.get_by_hostname(hostname)
    if not tunnel:
        logging.debug("!no tunnel, closing ({0})".format(
            hostname))
        socket.close()
        return

    conn, proxy_used = tunnel.pop_proxy_conn(timeout=2)
    if not conn:
        logging.debug("!no proxy connection, closing")
        socket.close()
        return

    protocol.send_message(conn, protocol.proxy_reply())
    pool = util.join_sockets(conn, socket)
    proxy_used.send(pool)
    logging.debug("popped connection:\"{0}\" for frontend:\"{1}\"".format(
                tunnel.name, hostname))
    pool.waitall()
