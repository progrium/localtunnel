import os

port = int(os.environ.get("WWW_PORT", 5000))
hostname = 'localtunnel.dotcloud.com'

service = 'localtunnel.server.TunnelBroker'
