import json
import time

import gevent.event

class Tunnel(object):
    MAX_BACKEND_SIZE = 8

    _tunnels = {}

    def __init__(self, name, ip, domain=None):
        self.name = name
        self.owner_ip = ip
        self.created = time.time()
        self.domain = domain
        self.backend_pool = []
        self.ready = gevent.event.Event()
        self.new = True

    def add_backend(self, socket):
        pool_size = len(self.backend_pool)
        if pool_size < Tunnel.MAX_BACKEND_SIZE:
            self.backend_pool.append(socket)
            if pool_size == 0: # before we added
                self.ready.set()
        else:
            raise ValueError("backend:\"{0}\" pool is full".format(
                    self.name))

    def pop_backend(self, wait_timeout=2):
        if not len(self.backend_pool):
            self.ready.wait(wait_timeout)
            if not len(self.backend_pool):
                return
            self.ready.clear()
        return self.backend_pool.pop()

    @classmethod
    def create(cls, obj):
        obj.pop('new', None)
        tunnel = Tunnel(**obj)
        cls._tunnels[tunnel.name] = tunnel
        return tunnel

    @classmethod
    def get_by_hostname(cls, hostname):
        name = hostname.split('.')[-3]
        tunnel = cls._tunnels.get(name)
        if not tunnel and tunnel.domain:
            for n, tunnel in cls._tunnels.iteritems():
                if hostname.endswith(tunnel.domain):
                    return tunnel
        else:
            return tunnel

    @classmethod
    def get_by_header(cls, header, ip):
        header['ip'] = ip
        if header['name'] in cls._tunnels:
            tunnel = cls._tunnels[header['name']]
            if tunnel.owner_ip != header['ip']:
                return
            if 'new' in header:
                return cls.create(header)
            return tunnel
        if 'new' in header:
            return cls.create(header)

