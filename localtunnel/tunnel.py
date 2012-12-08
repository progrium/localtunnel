import json
import time
import logging

import eventlet
import eventlet.semaphore

class Tunnel(object):
    max_backend_size = 8
    domain_part = 3
    backend_port = None
    cleanup_interval = 60

    _tunnels = {}

    def __init__(self, name, client, domain=None):
        self.name = name
        self.client = client
        self.created = time.time()
        self.updated = time.time()
        self.domain = domain
        self.backend_pool = []
        self.pool_semaphore = eventlet.semaphore.Semaphore(0)
        self.new = True

    def add_backend(self, socket):
        pool_size = len(self.backend_pool)
        if pool_size < Tunnel.max_backend_size:
            self.backend_pool.append(socket)
            self.pool_semaphore.release()
            self.updated = time.time()
        else:
            raise ValueError("backend:\"{0}\" pool is full".format(
                    self.name))

    def pop_backend(self, timeout=None):
        # TODO: timeout
        self.pool_semaphore.acquire()
        if not len(self.backend_pool):
            return
        return self.backend_pool.pop()

    @classmethod
    def create(cls, obj):
        obj.pop('new', None)
        tunnel = cls(**obj)
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
                raise RuntimeError("Tunnel name '{0}' is being used".format(
                        tunnel.name))
            if 'new' in header:
                return cls.create(header)
            return tunnel
        if 'new' in header:
            return cls.create(header)

    @classmethod
    def schedule_cleanup(cls):
        def _cleanup():
            to_remove = []
            for name, tunnel in cls._tunnels.iteritems():
                if time.time() - tunnel.updated > cls.cleanup_interval:
                    to_remove.append(name)
            tunnel_count = len(cls._tunnels)
            for name in to_remove:
                for backend in cls._tunnels[name].backend_pool:
                    backend.close()
                cls._tunnels.pop(name, None)
            if to_remove:
                logging.debug("Cleaned up {0} of {1} tunnels".format(
                    len(to_remove), tunnel_count))
            cls.schedule_cleanup()
        eventlet.spawn_after(cls.cleanup_interval, _cleanup)

