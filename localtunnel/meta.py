import json
import os

from eventlet.wsgi import Server

from localtunnel import __version__
from localtunnel.server.tunnel import Tunnel
from localtunnel.server import metrics

def root(environ, start_response):
    if environ['PATH_INFO'].startswith('/meta'):
        return meta(environ, start_response)
    else:
        start_response('200 OK', {})
        return [""]

def meta(environ, start_response):
    path = environ['PATH_INFO']
    start_response('200 OK', {})
    if path.startswith('/meta/version'):
        return [str(__version__)]
    elif path.startswith('/meta/backend'):
        return [str(os.environ.get('DOTCLOUD_SERVER_BACKEND_PORT', 
            Tunnel.backend_port))]
    elif path.startswith('/meta/metrics'):
        return [json.dumps(metrics.dump_metrics(),
            sort_keys=True, indent=2, separators=(',', ': '))]



server = Server(None, None, root)
