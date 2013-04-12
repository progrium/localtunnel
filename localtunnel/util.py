import json
import getpass
import socket
import urllib2
import urlparse
import platform

import eventlet
import eventlet.greenpool

import requests

def join_sockets(a, b):
    """ socket joining implementation """
    def _pipe(from_, to):
        while True:
            try:
                data = from_.recv(64 * 1024)
                if not data:
                    break
                try:
                    to.sendall(data)
                except:
                    from_.close()
                    break
            except:
                break
        try:
            to.close()
        except: 
            pass
    pool = eventlet.greenpool.GreenPool(size=2)
    pool.spawn_n(_pipe, a, b)
    pool.spawn_n(_pipe, b, a)
    return pool

def client_name():
    """ semi-unique client identifier string """
    return "{0}@{1};{2}".format(
        getpass.getuser(), 
        socket.gethostname(),
        platform.system())

def parse_address(address, default_port=None, default_ip=None):
    """ 
    returns address (ip, port) and hostname from anything like:
      localhost:8000
      8000
      :8000
      myhost:80
      0.0.0.0:8000
    """
    default_ip = default_ip or '0.0.0.0'
    try:
        # this is if address is simply a port number
        return (default_ip, int(address)), None
    except ValueError:
        parsed = urlparse.urlparse("tcp://{0}".format(address))
        try:
            if socket.gethostbyname(parsed.hostname) == parsed.hostname:
                # hostname is an IP
                return (parsed.hostname, parsed.port or default_port), None
        except socket.error:
            # likely, hostname is a domain name that can't be resolved
            pass
        # hostname is a domain name
        return (default_ip, parsed.port or default_port), parsed.hostname


def discover_backend_port(hostname, frontend_port=80):
    resp = requests.get('http://{0}/meta/backend'.format(hostname))
    if resp.status_code == 200:
        return int(resp.text)
    else:
        raise RuntimeError("Frontend failed to provide backend port")

def lookup_server_version(hostname):
    resp = requests.get('http://{0}/meta/version'.format(hostname))
    if resp.status_code == 200:
        return resp.text
    else:
        raise RuntimeError("Server failed to provide version")

def print_server_metrics(hostname):
    resp = requests.get('http://{0}/meta/metrics'.format(hostname))
    if resp.status_code == 200:
        for metric in resp.json:
            print "%(name) -40s %(value)s" % metric
    else:
        raise RuntimeError("Server failed to provide metrics")

