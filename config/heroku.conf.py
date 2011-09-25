import os

port = os.environ.get("PORT", 5000)
hostname = 'v2.localtunnel.com'

def service():
    from localtunnel.server import TunnelBroker
    return TunnelBroker()