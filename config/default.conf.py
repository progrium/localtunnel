port = 9999
hostname = 'localtunnel.local'

def service():
    from localtunnel.server import TunnelBroker
    return TunnelBroker()