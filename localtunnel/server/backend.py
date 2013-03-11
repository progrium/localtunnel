import json
import logging
import re

import eventlet
from eventlet.timeout import Timeout

from localtunnel.server.tunnel import Tunnel
from localtunnel import util
from localtunnel import protocol
from localtunnel import __version__
from localtunnel.server import metrics

HOST_TEMPLATE = "{0}.{1}"
BANNER = """Thanks for trying localtunnel v2 beta!
  Source code: https://github.com/progrium/localtunnel
  Donate: http://j.mp/donate-localtunnel
"""
HEARTBEAT_INTERVAL = 5

@metrics.meter_calls(name='backend_conn')
def connection_handler(socket, address):
    """ simple dispatcher for backend connections """
    try:
        protocol.assert_protocol(socket)
        message = protocol.recv_message(socket)
        if message and 'control' in message:
            handle_control_request(socket, message['control'])
        elif message and 'proxy' in message:
            handle_proxy_request(socket, message['proxy'])
        else:
            logging.debug("!backend: no request message, closing")
    except AssertionError:
        logging.debug("!backend: invalid protocol, closing")

@metrics.time_calls(name='control_conn')
def handle_control_request(socket, request):
    try:
        tunnel = Tunnel.get_by_control_request(request)
    except RuntimeError, e:
        protocol.send_message(socket, error_reply('notavailable'))
        socket.close()
        return
    protocol.send_message(socket, protocol.control_reply(
        host=HOST_TEMPLATE.format(tunnel.name, Tunnel.domain_suffix),
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

@metrics.time_calls(name='proxy_conn')
def handle_proxy_request(socket, request):
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
        proxy_used = tunnel.add_proxy_conn(socket)
        logging.debug("added connection:\"{0}\" by client:\"{1}\"".format(
            tunnel.name, tunnel.client))
        pool = proxy_used.wait()
        pool.waitall()
    except ValueError, e:
        logging.debug(str(e))
