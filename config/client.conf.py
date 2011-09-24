client_port = 8098
port = 9999
hostname = 'localtunnel.local'

def service():
    from localtunnel.server import TunnelClient
    return TunnelClient()