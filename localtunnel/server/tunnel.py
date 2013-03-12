import json
import re
import time
import logging

import eventlet
import eventlet.event
import eventlet.timeout
import eventlet.semaphore

from localtunnel.server import metrics

class Tunnel(object):
    max_pool_size = 3
    domain_suffix = None
    backend_port = None
    active_timeout = 5 * 60

    _tunnels = {}

    def __init__(self, name, client, protect=None, domain=None):
        self.name = name
        self.client = client
        if protect:
            user, passwd = protect.split(':')
            self.protect_user = user
            self.protect_passwd = passwd
            self.protect = True
        else:
            self.protect = False
        self.domain = domain
        self.created = time.time()
        self.updated = time.time()
        self.idle = False
        self.proxy_pool = []
        self.pool_semaphore = eventlet.semaphore.Semaphore(0)

        metrics.counter('total_tunnel').inc()
        platform = self.client.split(';', 1)[-1].lower()
        metrics.counter('collect:{0}'.format(platform)).inc()

    def add_proxy_conn(self, socket):
        pool_size = len(self.proxy_pool)
        if pool_size < Tunnel.max_pool_size:
            used = eventlet.event.Event()
            self.proxy_pool.append((socket, used))
            self.pool_semaphore.release()
            self.updated = time.time()
            self.idle = False
            return used
        else:
            raise ValueError("backend:\"{0}\" pool is full".format(
                    self.name))

    def pop_proxy_conn(self, timeout=None):
        with eventlet.timeout.Timeout(timeout, False):
            self.pool_semaphore.acquire()
        if not len(self.proxy_pool):
            return None, None
        return self.proxy_pool.pop()

    def destroy(self):
        cls = self.__class__ 
        for conn, _ in self.proxy_pool:
            conn.close()
        if self == cls._tunnels[self.name]:
            cls._tunnels.pop(self.name, None)
        metrics.counter('total_tunnel').dec()


    @classmethod
    def create(cls, obj):
        tunnel = cls(**obj)
        cls._tunnels[tunnel.name] = tunnel
        return tunnel

    @classmethod
    def get_by_hostname(cls, hostname):
        if not hostname.endswith(Tunnel.domain_suffix):
            return
        match = re.match('(.+?\.|)(\w+)\.$', hostname[:-len(Tunnel.domain_suffix)])
        if match:
            return cls._tunnels.get(match.group(2))

    @classmethod
    def get_by_control_request(cls, request):
        if request['name'] in cls._tunnels:
            tunnel = cls._tunnels[request['name']]
            if tunnel.client != request['client']:
                raise RuntimeError("Tunnel name '{0}' is being used".format(
                        tunnel.name))
            else:
                tunnel.destroy()
        return cls.create(request)

    @classmethod
    def get_by_proxy_request(cls, request):
        if request['name'] in cls._tunnels:
            tunnel = cls._tunnels[request['name']]
            if tunnel.client != request['client']:
                raise RuntimeError("Tunnel name '{0}' is being used".format(
                        tunnel.name))
            return tunnel

    @classmethod
    def schedule_idle_scan(cls):
        def _scan_idle():
            counter = metrics.counter('idle_tunnel')
            counter.clear()
            for name, tunnel in cls._tunnels.iteritems():
                if time.time() - tunnel.updated > cls.active_timeout:
                    tunnel.idle = True
                    counter.inc()
            if counter.get_count():
                logging.debug("scan: {0} of {1} tunnels are idle".format(
                    counter.get_value(), len(cls._tunnels)))
            cls.schedule_idle_scan()
        eventlet.spawn_after(cls.active_timeout, _scan_idle)

