Localtunnel v2 (Beta)
=====================

Localtunnel lets you expose a local web server to the public Internet.

For example, running a web server on port 8000 on your laptop can be
made public with::

    $ localtunnel-beta 8000
      Port 8000 is now accessible from http://8fde2c.v2.localtunnel.com ...

The localtunnel server is provided as a free public service. However, you
can also deploy your own localtunnel server on dotCloud or your own
server.

Installing
----------
Localtunnel currently requires Python 2.6 or greater. Install with pip::

    $ pip install localtunnel
    
Since there is one dependency with a C extension, you will need Python
headers and basic build tools. If you're on OS X this just means you need
to have Xcode installed.

License
-------
MIT
