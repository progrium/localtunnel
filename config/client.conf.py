client_port = 8098
port = 9999
hostname = 'localhost'

def service():
    from localtunnel.server import TunnelClient
    return TunnelClient()