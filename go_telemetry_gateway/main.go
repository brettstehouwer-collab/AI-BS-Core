package main

import (
	"fmt"
	"net/http"
)

func main() {
	http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "High-Performance Go WebSocket Gateway Active")
	})
	fmt.Println("Go Micro-service listening on port 8080...")
	// http.ListenAndServe(":8080", nil)
}
