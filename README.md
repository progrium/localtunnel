# localtunnel

What happened to localtunnel? After pioneering instant public tunnels to localhost, many people copied the project and started businesses around the idea. Localtunnel fell into obscurity. Today, Alan Shreve's [Ngrok](https://ngrok.com) rightly dominates mindshare on the idea. 

This repo now contains localtunnel v3, a very minimal implementation (under 200 lines) written in Go using my new project [Duplex](https://github.com/progrium/duplex). Duplex lets you make stuff like localtunnel very easily. Although usable, there is no public server and the scope of the project is pretty fixed where it is.

This repo also continues to exist to archive the history of the project. You'll find several interesting branches here:

 * [v2](https://github.com/progrium/localtunnel/tree/v2) (2011-2013) - Attempt to revitalize the project and service, v2 was written end-to-end in Python gevent and resolved many issues and requests from v1.
 * [v1](https://github.com/progrium/localtunnel/tree/v1) (mid 2010) - The original implementation that became popular. It worked quite well, but was a dirty hack. It wrapped OpenSSH, with a client in Ruby and a control server in Python Twisted.
 * [prototype](https://github.com/progrium/localtunnel/tree/prototype) (early 2010) - When I first had the idea, I tried using Python Twisted to implement the whole system. I didn't have the experience to get stream multiplexing to work, so this version is pretty broken.

## Using localtunnel v3

Binary releases have not been set up yet, so you'll need Go to get started:

	$ go install github.com/progrium/localtunnel


## License

BSD