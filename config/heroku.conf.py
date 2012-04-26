import os

port = int(os.environ.get("PORT", 5000))
hostname = 'localtunnel.heroku'

service = 'localtunnel.server.TunnelBroker'
