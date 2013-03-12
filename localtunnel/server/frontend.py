import json
import logging
import re
import os
from socket import MSG_PEEK

from localtunnel.server.tunnel import Tunnel
from localtunnel import util
from localtunnel import meta
from localtunnel import protocol
from localtunnel.server import metrics

def peek_http_host(socket):
    host = ''
    hostheader = re.compile('host: ([^\(\);,<>]+)', re.I)
    # Peek up to 16 kilobytes into data for the Host header
    bytes = socket.recv(1024 * 16, MSG_PEEK)
    if not bytes:
        return host
    for line in bytes.split('\r\n'):
        match = hostheader.match(line)
        if match:
            host = match.group(1)
    return host

def send_http_error(socket, content, status=None):
    status = status or '500 Internal Error'
    data =  """HTTP/1.1 {0}\r\nContent-Length: {1}\r\nConnection: close\r\n\r\n{2}
            """.format(status, len(str(content)), content).strip()
    socket.sendall(data)
    socket.close()
    logging.debug("!{0}".format(content.lower()))


@metrics.time_calls(name='frontend_conn')
def connection_handler(socket, address):
    hostname = peek_http_host(socket)
    if not hostname:
        send_http_error(socket, 'No hostname', '400 Bad Request')
        return

    if hostname == Tunnel.domain_suffix:
        meta.server.process_request((socket, address))
        return

    tunnel = Tunnel.get_by_hostname(hostname)
    if not tunnel:
        send_http_error(socket, 'No tunnel for {0}'.format(hostname), '410 Gone')
        return

    conn, proxy_used = tunnel.pop_proxy_conn(timeout=2)
    if not conn:
        send_http_error(socket, 'No proxy connections', '502 Bad Gateway')
        return

    protocol.send_message(conn, protocol.proxy_reply())
    pool = util.join_sockets(conn, socket)
    proxy_used.send(pool)
    logging.debug("popped connection:\"{0}\" for frontend:\"{1}\"".format(
                tunnel.name, hostname))
    pool.waitall()
