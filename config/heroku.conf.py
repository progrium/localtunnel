port = 80
hostname = 'v2.localtunnel.com'

def service():
    from localtunnel.server import TunnelBroker
    return TunnelBroker()