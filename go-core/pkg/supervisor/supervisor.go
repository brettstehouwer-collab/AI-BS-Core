package supervisor

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"sync"
	"time"
)

// All mutable daemon state is guarded by Supervisor.lock.
type ManagedDaemon struct {
	Name         string
	Cmd          []string
	Cwd          string
	AutoRestart  bool
	AutoStart    bool
	RestartCount int
	MaxRestarts  int
	BackoffBase  time.Duration
	Cancel       context.CancelFunc
	process      *os.Process
	done         chan struct{}
	state        string
	lastError    string
	adopted      bool
	pidFilePath  string
}
type Supervisor struct {
	Daemons map[string]*ManagedDaemon
	lock    sync.Mutex
}

// HandoffEntry pins a running process to its executable and Windows creation time.
// PID zero explicitly leaves a registered daemon stopped, even if AutoStart is true.
type HandoffEntry struct {
	PID              int      `json:"pid"`
	CreationFiletime string   `json:"creation_filetime"`
	Executable       string   `json:"executable"`
	Command          []string `json:"command"`
}

func NewSupervisor() *Supervisor { return &Supervisor{Daemons: make(map[string]*ManagedDaemon)} }
func (s *Supervisor) Register(name string, cmd []string, cwd string, autoRestart, autoStart bool) {
	s.lock.Lock()
	defer s.lock.Unlock()
	if _, ok := s.Daemons[name]; ok {
		log.Printf("[Supervisor] Already registered: %s", name)
		return
	}
	stateDir := filepath.Join(cwd, "state")
	os.MkdirAll(stateDir, 0755)
	s.Daemons[name] = &ManagedDaemon{Name: name, Cmd: append([]string(nil), cmd...), Cwd: cwd, AutoRestart: autoRestart, AutoStart: autoStart, MaxRestarts: 5, BackoffBase: 3 * time.Second, state: "stopped", pidFilePath: filepath.Join(stateDir, name+".pid")}
}
func (s *Supervisor) startLocked(d *ManagedDaemon, existing *os.Process) {
	ctx, cancel := context.WithCancel(context.Background())
	d.Cancel = cancel
	d.done = make(chan struct{})
	d.RestartCount = 0
	d.lastError = ""
	d.process = existing
	d.adopted = existing != nil
	d.state = "starting"
	if existing != nil {
		d.state = "running"
		os.WriteFile(d.pidFilePath, []byte(fmt.Sprint(existing.Pid)), 0644)
	}
	go s.watchdog(d, ctx, existing)
}
func (s *Supervisor) StartAll() {
	s.lock.Lock()
	defer s.lock.Unlock()
	for _, d := range s.Daemons {
		if d.AutoStart && d.Cancel == nil {
			s.startLocked(d, nil)
		}
	}
}

// RestoreHandoff validates the entire snapshot before monitoring any process.
// It never launches a process while restoring; only already-running entries are adopted.
func (s *Supervisor) RestoreHandoff(path string) error {
	return s.restoreHandoff(path, false)
}

// ValidateHandoff performs the same identity checks without changing daemon state.
func (s *Supervisor) ValidateHandoff(path string) error {
	return s.restoreHandoff(path, true)
}

func (s *Supervisor) restoreHandoff(path string, validateOnly bool) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	if len(data) > 1024*1024 {
		return fmt.Errorf("handoff manifest too large")
	}
	entries := map[string]HandoffEntry{}
	decoder := json.NewDecoder(strings.NewReader(string(data)))
	decoder.DisallowUnknownFields()
	if err = decoder.Decode(&entries); err != nil {
		return err
	}
	s.lock.Lock()
	defer s.lock.Unlock()
	if len(entries) != len(s.Daemons) {
		return fmt.Errorf("handoff must cover every registered daemon")
	}
	opened := map[string]*os.Process{}
	committed := false
	defer func() {
		if !committed {
			for _, p := range opened {
				p.Release()
			}
		}
	}()
	for name, d := range s.Daemons {
		if d.Cancel != nil {
			return fmt.Errorf("%s is already supervised", name)
		}
		entry, ok := entries[name]
		if !ok || !reflect.DeepEqual(entry.Command, d.Cmd) {
			return fmt.Errorf("handoff command mismatch for %s", name)
		}
		if entry.PID == 0 {
			continue
		}
		if entry.PID < 0 {
			return fmt.Errorf("invalid PID for %s", name)
		}
		// Open first so the process object remains referenced throughout identity validation.
		p, err := os.FindProcess(entry.PID)
		if err != nil {
			return fmt.Errorf("%s: %w", name, err)
		}
		opened[name] = p
		identity, err := inspectProcess(entry.PID)
		if err != nil {
			return fmt.Errorf("%s: %w", name, err)
		}
		if identity.CreationFiletime != entry.CreationFiletime || !strings.EqualFold(filepath.Clean(identity.Executable), filepath.Clean(entry.Executable)) {
			return fmt.Errorf("handoff process identity mismatch for %s", name)
		}
	}
	if validateOnly {
		return nil
	}
	for name, p := range opened {
		s.startLocked(s.Daemons[name], p)
	}
	committed = true
	return nil
}
func (s *Supervisor) StopAll() {
	s.lock.Lock()
	var waits []chan struct{}
	for _, d := range s.Daemons {
		if d.Cancel != nil {
			d.state = "stopping"
			d.Cancel()
			waits = append(waits, d.done)
		}
	}
	s.lock.Unlock()
	for _, done := range waits {
		select {
		case <-done:
		case <-time.After(10 * time.Second):
			log.Printf("[Supervisor] Timed out waiting for shutdown")
		}
	}
}
func (s *Supervisor) StartDaemon(name string) error {
	s.lock.Lock()
	defer s.lock.Unlock()
	d, ok := s.Daemons[name]
	if !ok {
		return fmt.Errorf("daemon %q not found", name)
	}
	if d.Cancel != nil {
		return fmt.Errorf("daemon %q is already active", name)
	}
	s.startLocked(d, nil)
	return nil
}
func (s *Supervisor) StopDaemon(name string) error {
	s.lock.Lock()
	d, ok := s.Daemons[name]
	if !ok {
		s.lock.Unlock()
		return fmt.Errorf("daemon %q not found", name)
	}
	if d.Cancel == nil {
		s.lock.Unlock()
		return fmt.Errorf("daemon %q is not active", name)
	}
	d.state = "stopping"
	d.Cancel()
	done := d.done
	s.lock.Unlock()
	select {
	case <-done:
		return nil
	case <-time.After(10 * time.Second):
		return fmt.Errorf("daemon %q is still stopping", name)
	}
}
func (s *Supervisor) GetStatus() map[string]interface{} {
	s.lock.Lock()
	defer s.lock.Unlock()
	result := map[string]interface{}{}
	for name, d := range s.Daemons {
		pid := -1
		if d.process != nil {
			pid = d.process.Pid
		}
		result[name] = map[string]interface{}{"running": d.process != nil, "pid": pid, "auto_restart": d.AutoRestart, "auto_start": d.AutoStart, "state": d.state, "adopted": d.adopted, "restart_count": d.RestartCount, "last_error": d.lastError}
	}
	return result
}
func waitExisting(ctx context.Context, p *os.Process) error {
	done := make(chan error, 1)
	go func() {
		state, err := p.Wait()
		if err == nil && !state.Success() {
			err = fmt.Errorf("process exited with code %d", state.ExitCode())
		}
		done <- err
	}()
	select {
	case err := <-done:
		return err
	case <-ctx.Done():
		if err := p.Kill(); err != nil && err != os.ErrProcessDone {
			// Keep monitoring a process that could not be stopped. Reporting it
			// stopped would allow a duplicate start while it is still alive.
			log.Printf("[Supervisor] Cannot stop adopted PID %d: %v", p.Pid, err)
		}
		return <-done
	}
}
func (s *Supervisor) watchdog(d *ManagedDaemon, ctx context.Context, existing *os.Process) {
	defer func() {
		s.lock.Lock()
		d.process = nil
		d.Cancel = nil
		d.adopted = false
		if d.state != "failed" {
			d.state = "stopped"
		}
		close(d.done)
		s.lock.Unlock()
	}()
	for {
		if ctx.Err() != nil && existing == nil {
			return
		}
		var err error
		var pid int
		if existing != nil {
			pid = existing.Pid
			err = waitExisting(ctx, existing)
			existing = nil
		} else {
			pid, err = s.runProcess(d, ctx)
		}
		s.lock.Lock()
		d.process = nil
		d.adopted = false
		if raw, e := os.ReadFile(d.pidFilePath); e == nil && strings.TrimSpace(string(raw)) == fmt.Sprint(pid) {
			os.Remove(d.pidFilePath)
		}
		if err != nil {
			d.lastError = err.Error()
		}
		if ctx.Err() != nil || !d.AutoRestart {
			s.lock.Unlock()
			return
		}
		d.RestartCount++
		if d.RestartCount > d.MaxRestarts {
			d.state = "failed"
			s.lock.Unlock()
			return
		}
		d.state = "backoff"
		delay := d.BackoffBase * time.Duration(d.RestartCount)
		s.lock.Unlock()
		select {
		case <-time.After(delay):
		case <-ctx.Done():
			return
		}
	}
}
func (s *Supervisor) runProcess(d *ManagedDaemon, ctx context.Context) (int, error) {
	if len(d.Cmd) == 0 {
		return 0, fmt.Errorf("empty daemon command")
	}
	cmd := exec.CommandContext(ctx, d.Cmd[0], d.Cmd[1:]...)
	cmd.Dir = d.Cwd
	cmd.Env = append(os.Environ(), "DAEMON_MANAGER_OWNED=1")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	configureProcess(cmd)
	s.lock.Lock()
	d.state = "starting"
	err := cmd.Start()
	if err != nil {
		s.lock.Unlock()
		return 0, err
	}
	d.process = cmd.Process
	d.state = "running"
	pid := cmd.Process.Pid
	os.WriteFile(d.pidFilePath, []byte(fmt.Sprint(pid)), 0644)
	s.lock.Unlock()
	log.Printf("[Supervisor] %s started with PID %d", d.Name, pid)
	return pid, cmd.Wait()
}
