package main

import (
	"log"
	"net"
	"time"

	"github.com/inconshreveable/go-vhost"
	"github.com/progrium/duplex/poc2/duplex"
)

func server(backendListen, frontendListen string) {
	// bind frontend
	frontend, err := net.Listen("tcp", frontendListen)
	if err != nil {
		log.Fatal(err)
	}
	log.Println("frontend listening on", frontendListen, "...")
	mux, err := vhost.NewHTTPMuxer(frontend, 1*time.Second)
	if err != nil {
		log.Fatal(err)
	}
	go func() {
		for {
			conn, err := mux.NextError()
			log.Println("vhost:", err)
			if conn != nil {
				conn.Write([]byte("error: " + err.Error()))
				conn.Close()
			}
		}
	}()

	// bind backend
	backend := duplex.NewPeer()
	err = backend.Bind("tcp://" + backendListen)
	if err != nil {
		log.Fatal(err)
	}
	log.Println("backend listening on", backendListen, "...")
	for {
		meta, ch := backend.Accept()
		if meta == nil {
			break
		}
		// register vhost
		if meta.Service() == "tunnel" {
			log.Println("registering", meta.RemotePeer())
			vhostListener, err := mux.Listen(meta.RemotePeer())
			if err != nil {
				log.Println(err)
			}
			go func() {
				for {
					conn, err := vhostListener.Accept()
					if err != nil {
						log.Println(err)
					}
					tunnelCh, err := ch.Open("", nil)
					if err != nil {
						log.Println(err)
					}
					go tunnelCh.Join(conn)
				}
			}()
			continue
		}
	}
}
