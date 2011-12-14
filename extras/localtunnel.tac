import imp

from twisted.application import service
from twisted.python.log import ILogObserver
from twisted.python.syslog import SyslogObserver

server = imp.load_source('server', '/home/deploy/localtunnel/server.py') 

application = service.Application('localtunnel')
application.setComponent(ILogObserver, SyslogObserver('localtunnel').emit)
service = server.getWebService(
    user='deploy', 
    host_name='localtunnel.{you}.com',
    address='127.0.0.1',
    port=8080, 
    provider='{you}',
    strip_subdomain=False)
service.setServiceParent(application)
