package main

import (
	"log"
	"net"

	"github.com/progrium/duplex/poc2/duplex"
)

func client(backendConnect, localConnect, vhostName string) {
	client := duplex.NewPeer()
	client.SetOption(duplex.OptName, vhostName)
	err := client.Connect("tcp://" + backendConnect)
	if err != nil {
		log.Fatal(err)
	}
	tunnel, err := client.Open(client.NextPeer(), "tunnel", nil)
	if err != nil {
		log.Fatal(err)
	}
	for {
		meta, ch := tunnel.Accept()
		if meta == nil {
			break
		}
		go func() {
			conn, err := net.Dial("tcp", localConnect)
			if err != nil {
				log.Println(err)
				ch.Close()
				return
			}
			println("connection received")
			ch.Join(conn)
		}()
	}
}
