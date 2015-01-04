package main

import (
	"flag"
)

var serverMode = flag.Bool("s", false, "run in server mode")

func main() {
	flag.Parse()

	if *serverMode {
		server(flag.Arg(0), flag.Arg(1))
	} else {
		client(flag.Arg(0), flag.Arg(1), flag.Arg(2))
	}
}
