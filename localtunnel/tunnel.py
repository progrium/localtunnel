import json
import time

import gevent.coros

class Tunnel(object):
    max_backend_size = 8
    domain_part = 3
    backend_port = None

    _tunnels = {}

    def __init__(self, name, client, domain=None):
        self.name = name
        self.client = client
        self.created = time.time()
        self.domain = domain
        self.backend_pool = []
        self.pool_semaphore = gevent.coros.Semaphore(0)
        self.new = True

    def add_backend(self, socket):
        pool_size = len(self.backend_pool)
        if pool_size < Tunnel.max_backend_size:
            self.backend_pool.append(socket)
            self.pool_semaphore.release()
        else:
            raise ValueError("backend:\"{0}\" pool is full".format(
                    self.name))

    def pop_backend(self, timeout=None):
        self.pool_semaphore.acquire(timeout=timeout)
        if not len(self.backend_pool):
            return
        return self.backend_pool.pop()

    @classmethod
    def create(cls, obj):
        obj.pop('new', None)
        tunnel = Tunnel(**obj)
        cls._tunnels[tunnel.name] = tunnel
        return tunnel

    @classmethod
    def get_by_hostname(cls, hostname):
        name = hostname.split('.')[-1 * Tunnel.domain_part]
        tunnel = cls._tunnels.get(name)
        if not tunnel:
            for n, tunnel in cls._tunnels.iteritems():
                if hostname.endswith(tunnel.domain):
                    return tunnel
        else:
            return tunnel

    @classmethod
    def get_by_header(cls, header):
        if header['name'] in cls._tunnels:
            tunnel = cls._tunnels[header['name']]
            if tunnel.client != header['client']:
                return
            if 'new' in header:
                return cls.create(header)
            return tunnel
        if 'new' in header:
            return cls.create(header)

