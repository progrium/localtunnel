import os

port = int(os.environ.get("WWW_PORT", 5000))
hostname = 'localtunnel-progrium.dotcloud.com'

service = 'localtunnel.server.TunnelBroker'
