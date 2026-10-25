package main

import (
	"errors"
	"testing"
)

type startupFixture struct {
	starts   int
	restores []string
	err      error
}

func (s *startupFixture) StartAll() { s.starts++ }
func (s *startupFixture) RestoreHandoff(path string) error {
	s.restores = append(s.restores, path)
	return s.err
}

func TestDefaultStartupDoesNotLaunchDaemons(t *testing.T) {
	s := &startupFixture{}
	if err := configureSupervision(s, "", false); err != nil {
		t.Fatal(err)
	}
	if s.starts != 0 || len(s.restores) != 0 {
		t.Fatal("default gateway startup changed daemon ownership")
	}
}
func TestExplicitManagementStartsRegisteredFleet(t *testing.T) {
	s := &startupFixture{}
	if err := configureSupervision(s, "", true); err != nil {
		t.Fatal(err)
	}
	if s.starts != 1 || len(s.restores) != 0 {
		t.Fatal("explicit management was not dispatched exactly once")
	}
}
func TestHandoffOnlyRestoresTheSelectedOwnership(t *testing.T) {
	s := &startupFixture{}
	if err := configureSupervision(s, "fixture.json", false); err != nil {
		t.Fatal(err)
	}
	if s.starts != 0 || len(s.restores) != 1 || s.restores[0] != "fixture.json" {
		t.Fatal("handoff silently started a fleet")
	}
}
func TestConflictingStartupOptionsDoNothing(t *testing.T) {
	s := &startupFixture{}
	if err := configureSupervision(s, "fixture.json", true); err == nil {
		t.Fatal("conflicting startup accepted")
	}
	if s.starts != 0 || len(s.restores) != 0 {
		t.Fatal("conflicting startup changed services")
	}
}
func TestHandoffFailureIsPreservedWithoutFallback(t *testing.T) {
	failure := errors.New("fixture invalid handoff")
	s := &startupFixture{err: failure}
	if err := configureSupervision(s, "fixture.json", false); !errors.Is(err, failure) {
		t.Fatal("handoff error hidden")
	}
	if s.starts != 0 {
		t.Fatal("handoff failure started default fleet")
	}
}
