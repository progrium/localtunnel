import logging

import requests
import eventlet

from yunomi import dump_metrics
from yunomi import counter
from yunomi import *

requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

report_interval = 30
monitored_metrics = """
total_tunnel_count
collect:darwin_count
collect:linux_count
collect:windows_count
idle_tunnel_count
control_conn_avg
frontend_conn_5m_rate
""".split("\n")[1:-1]

class StatHat(object):
    """The StatHat API wrapper."""
    STATHAT_URL = 'http://api.stathat.com'

    def __init__(self, key=None, prefix=None):
        self.key = key
        self.prefix = prefix or ''
        # Enable keep-alive and connection-pooling.
        self.session = requests.session()

    def _http_post(self, path, data):
        url = self.STATHAT_URL + path
        r = self.session.post(url, data=data, prefetch=True)
        return r

    def value(self, name, value):
        r = self._http_post('/ez', {
            'ezkey': self.key, 
            'stat': ''.join([self.prefix, name]), 
            'value': value})
        return r.ok

    def count(self, name, count):
        r = self._http_post('/ez', {
            'ezkey': self.key, 
            'stat': ''.join([self.prefix, name]), 
            'count': count})
        return r.ok

def run_reporter(stats_key):
    stats = StatHat(stats_key, 'localtunnel.')
    logging.info("starting metrics reporter with {0}".format(stats_key))
    def _report_stats():
        dump = {}
        for m in dump_metrics():
            dump[m['name']] = m['value']
        for metric in monitored_metrics:
            value = dump.get(metric)
            if value:
                if metric.startswith('collect:'):
                    # metrics starting with "collect:" are
                    # counters that will be reset once reported
                    stats.count(metric.split(':')[-1], value)
                    metric_name = metric.split('_count')[0]
                    counter(metric_name).clear()
                else:
                    stats.value(metric, value)
        logging.debug("metrics reported")
        eventlet.spawn_after(report_interval, _report_stats)
    eventlet.spawn_after(report_interval, _report_stats)


