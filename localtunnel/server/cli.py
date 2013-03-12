import argparse
import logging
import os

import eventlet
import eventlet.debug
import eventlet.greenpool

from localtunnel.server.tunnel import Tunnel
from localtunnel import util
from localtunnel.server import backend
from localtunnel.server import frontend
from localtunnel.server import metrics

def run():
    eventlet.debug.hub_prevent_multiple_readers(False)
    eventlet.monkey_patch(socket=True)

    logging.basicConfig(
        format="%(asctime)s %(levelname) 7s %(module)s: %(message)s",
        level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Localtunnel server daemon')
    parser.add_argument('frontend', metavar='frontend_listener', type=str,
        help='hostname to run frontend on (default: vcap.me:8000)', 
        default='vcap.me:8000')
    parser.add_argument('backend', metavar='backend_listener', type=str,
        help='port or address to run backend server on (default: 8001)',
        default='8001')
    args = parser.parse_args()
    
    frontend_address, frontend_hostname = util.parse_address(args.frontend)
    backend_address, backend_hostname = util.parse_address(args.backend)

    logging.info("starting frontend on {0} for {1}...".format(
        frontend_address, frontend_hostname))
    logging.info("starting backend on {0}...".format(backend_address))
    
    Tunnel.backend_port = backend_address[1]
    if frontend_address[1] == 80:
        Tunnel.domain_suffix = frontend_hostname
    else:
        Tunnel.domain_suffix = ":".join(
            [frontend_hostname, str(frontend_address[1])])
    
    stats_key = os.environ.get('STATHAT_EZKEY', None)
    if stats_key:
        metrics.run_reporter(stats_key)
    
    frontend_listener = eventlet.listen(frontend_address)
    backend_listener = eventlet.listen(backend_address)
    
    try:
        Tunnel.schedule_idle_scan()
        pool = eventlet.greenpool.GreenPool(size=2)
        pool.spawn_n(eventlet.serve, frontend_listener,
                frontend.connection_handler)
        pool.spawn_n(eventlet.serve, backend_listener,
                backend.connection_handler)
        pool.waitall()
    except KeyboardInterrupt:
        pass
