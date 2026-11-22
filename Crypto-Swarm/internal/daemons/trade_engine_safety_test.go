package daemons

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"testing"
)

type auditNoNetworkTransport struct{ calls int }

func (s *auditNoNetworkTransport) RoundTrip(r *http.Request) (*http.Response, error) {
	s.calls++
	return nil, fmt.Errorf("unexpected network request")
}

func TestCreateOrderHeldBeforeAnyNetwork(t *testing.T) {
	spy := &auditNoNetworkTransport{}
	original := http.DefaultTransport
	http.DefaultTransport = spy
	t.Cleanup(func() { http.DefaultTransport = original })
	client := &CryptoComClient{APIKey: "fixture", APISecret: "fixture"}
	for _, side := range []string{"BUY", "SELL"} {
		id, notional, err := client.CreateOrder("CRO/USD", side, 100)
		if err == nil || !strings.Contains(err.Error(), "held") || id != "" || notional != 0 {
			t.Fatalf("unexpected dispatch result: id=%q, notional=%v, err=%v", id, notional, err)
		}
	}
	if spy.calls != 0 {
		t.Fatalf("made %d network calls", spy.calls)
	}
}

func TestPrivateCreateOrderCannotBypassHold(t *testing.T) {
	spy := &auditNoNetworkTransport{}
	original := http.DefaultTransport
	http.DefaultTransport = spy
	t.Cleanup(func() { http.DefaultTransport = original })
	client := &CryptoComClient{APIKey: "fixture", APISecret: "fixture"}
	result, err := client.doRequest("private/create-order", nil)
	if err == nil || result != nil || client.reqID != 0 || spy.calls != 0 {
		t.Fatalf("private request bypassed hold: id=%d, calls=%d, err=%v", client.reqID, spy.calls, err)
	}
}

func TestWatcherDoesNotTouchTrackingStateDuringHold(t *testing.T) {
	// Nil dependencies would panic if a worker were admitted past the hold.
	StartWatcher(context.Background(), nil, nil)
}

func TestDiamondDoesNotTouchLedgerDuringHold(t *testing.T) {
	StartDiamondHand(context.Background(), nil, nil)
}
