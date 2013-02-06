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
    parser.add_argument('frontend_port', metavar='frontend_port', type=int,
                help='port to run public frontend', default=8000)
    parser.add_argument('backend_port', metavar='backend_port', type=int,
                help='port to run backend server', default=8001)
    parser.add_argument('domain_suffix', metavar='domain_suffix', type=str,
                help='domain suffix (from the right) to extract tunnel name')
    args = parser.parse_args()
    
    logging.info("starting frontend on {0}...".format(args.frontend_port))
    logging.info("starting backend on {0}...".format(args.backend_port))
    
    Tunnel.backend_port = args.backend_port
    Tunnel.domain_suffix = args.domain_suffix
    
    stats_key = os.environ.get('STATHAT_EZKEY', None)
    if stats_key:
        metrics.run_reporter(stats_key)
    
    frontend_listener = eventlet.listen(('0.0.0.0', args.frontend_port))
    backend_listener = eventlet.listen(('0.0.0.0', args.backend_port))
    
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
