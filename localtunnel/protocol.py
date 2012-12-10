import struct
import json

VERSION = 'LTP/0.2'

ERRORS = {
    'unavailable': "This tunnel name is unavailable",
    'expired': "This tunnel has expired",
}

def assert_protocol(socket):
    protocol = socket.recv(len(VERSION))
    assert protocol == VERSION

def recv_message(socket):
    try:
        header = socket.recv(4)
        length = struct.unpack(">I", header)[0]
        data = socket.recv(length)
        message = json.loads(data)
        return message
    except:
        return

def send_message(socket, message):
    data = json.dumps(message)
    header = struct.pack(">I", len(data))
    socket.sendall(''.join([header, data]))

def control_request(name, client, protect=None, domain=None):
    request = dict(name=name, client=client)
    if protect:
        request['protect'] = protect
    if domain:
        request['domain'] = domain
    return {'control': request}

def control_reply(host, concurrency, banner=None):
    reply = dict(host=host, concurrency=concurrency)
    if banner:
        reply['banner'] = banner
    return {'control': reply}

def control_ping():
    return {'control': 'ping'}

def control_pong():
    return {'control': 'pong'}

def proxy_request(name, client):
    return {'proxy': dict(name=name, client=client)}

def proxy_reply():
    return {'proxy': True}

def error_reply(error):
    assert error in ERRORS
    return dict(error=error, message=ERRORS[error])

