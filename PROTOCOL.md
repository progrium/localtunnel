# Localtunnel Protocol

The Localtunnel Protocol (LTP) defines a lightweight protocol for a
client and server to establish a pool of connections used to proxy
connections from the server to the client. 

Editor: Jeff Lindsay <progrium@gmail.com><br />
Contributors: Jeff Lindsay <progrium@gmail.com>

## License

Copyright (c) 2012 Jeff Lindsay.

This Specification is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.

This Specification is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

## Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119[1].

## Goals

* Allow TCP connections to flow from the server to the client, where the
  server acts as a reverse proxy and the client provides backend
connections
* Avoid overhead of multiplexing by using one backend connection to
  tunnel each frontend conection
* Separate control channel from proxy channels as separate connections
* Allow long-lived tunnel sessions with heartbeating

## Overview

             +--------------------+
             | Localtunnel Server |
             |--------------------|         +----------+
             | Backend | Frontend |<--------+TCP Client|
             +---------+----------+         +----------+
                ^  ^^
                |  ||
                |  ||
         Control|  ||Proxy
      Connection|  ||Connections
                |  ||
             +--+--++-------------+         +----------+
             | Localtunnel Client +-------->|TCP Server|
             +--------------------+         +----------+

The protocol focuses on the interaction between a Localtunnel Server
Backend and a Localtunnel Client. It's implied but out of the scope of
this protocol the interaction between the other components. However,
it's important to know how the whole system works to understand the
function of this protocol.

The goal is to allow connections made by an arbitrary TCP Client to
connect to a TCP Server without direct network access. We assume a
Localtunnel Client can connect to a Localtunnel Server and the TCP
Server, and that the TCP Client can connect to the Localtunnel Server.

In order for a connection to be made from the TCP Client to the TCP
Server in this topology, the Localtunnel Client must first connect to
the Localtunnel Backend with a Control Connection. This represents a
tunnel session. It's used for setting up a tunnel and maintaining
heartbeats. In this connection, the Backend will dictate how many Proxy
Connections the Client should open to the Backend. These Proxy
Connections make up a pool of backends for the Localtunnel Frontend to
use as a reverse proxy.

Once a tunnel is established with a Control Connection and pool of at
least one Proxy Connection, the TCP Client can connect to the
Localtunnel Frontend. One of the Proxy Connections will be removed from
the pool and sent a signal for the Localtunnel Client to open a
connection to the TCP Server. The incoming Frontend connection will be
joined with the Proxy Connection on the Backend, and the Client will
then join the newly established connection to the TCP Server with the
open Proxy Connection.

Once these connections are joined, the connection is left alone for either
the TCP Client or TCP Server to close. 

We also assume the client will open a new Proxy Connection to the
Backend for every connection joined, maintaining a consistent Proxy
Connection pool.

This protocol addresses the interactions necessary on the Control
Connection and at the beginning of the Proxy Connection.

## Two Connection Types

### Control Connection

### Proxy Connection

## Protocol Header

## Request-Reply Preamble

## Heartbeats

