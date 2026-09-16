package supervisor

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"
)

// ManagedDaemon represents a background process.
type ManagedDaemon struct {
	Name           string
	Cmd            []string
	Cwd            string
	AutoRestart    bool
	AutoStart      bool
	RestartCount   int
	MaxRestarts    int
	BackoffBase    time.Duration
	Cancel         context.CancelFunc
	ctx            context.Context
	cmdInstance    *exec.Cmd
	lock           sync.Mutex
	pidFilePath    string
}

// Supervisor manages a collection of daemons.
type Supervisor struct {
	Daemons map[string]*ManagedDaemon
	lock    sync.Mutex
}

// NewSupervisor initializes a new supervisor.
func NewSupervisor() *Supervisor {
	return &Supervisor{
		Daemons: make(map[string]*ManagedDaemon),
	}
}

// Register adds a new daemon to the supervisor.
func (s *Supervisor) Register(name string, cmd []string, cwd string, autoRestart bool, autoStart bool) {
	s.lock.Lock()
	defer s.lock.Unlock()

	if _, exists := s.Daemons[name]; exists {
		log.Printf("[Supervisor] Warning: Daemon '%s' is already registered.", name)
		return
	}

	stateDir := filepath.Join(cwd, "state")
	os.MkdirAll(stateDir, 0755)

	s.Daemons[name] = &ManagedDaemon{
		Name:        name,
		Cmd:         cmd,
		Cwd:         cwd,
		AutoRestart: autoRestart,
		AutoStart:   autoStart,
		MaxRestarts: 5,
		BackoffBase: 3 * time.Second,
		pidFilePath: filepath.Join(stateDir, name+".pid"),
	}
	log.Printf("[Supervisor] Registered daemon '%s'.", name)
}

// StartAll launches all registered daemons in their own goroutines.
func (s *Supervisor) StartAll() {
	s.lock.Lock()
	defer s.lock.Unlock()

	for _, daemon := range s.Daemons {
		if !daemon.AutoStart {
			continue
		}
		
		ctx, cancel := context.WithCancel(context.Background())
		daemon.ctx = ctx
		daemon.Cancel = cancel

		go s.watchdog(daemon)
	}
}

// StopAll gracefully shuts down all daemons.
func (s *Supervisor) StopAll() {
	s.lock.Lock()
	defer s.lock.Unlock()
	log.Println("[Supervisor] Shutting down all daemons...")

	for _, daemon := range s.Daemons {
		if daemon.Cancel != nil {
			daemon.Cancel() // This signals the context to kill the process
		}
	}
}

// StartDaemon starts a specific daemon manually.
func (s *Supervisor) StartDaemon(name string) error {
	s.lock.Lock()
	daemon, exists := s.Daemons[name]
	if !exists {
		s.lock.Unlock()
		return fmt.Errorf("daemon '%s' not found", name)
	}
	
	if daemon.Cancel != nil {
		s.lock.Unlock()
		return fmt.Errorf("daemon '%s' is already running", name)
	}
	s.lock.Unlock()

	ctx, cancel := context.WithCancel(context.Background())
	daemon.ctx = ctx
	daemon.Cancel = cancel
	daemon.RestartCount = 0

	go s.watchdog(daemon)
	log.Printf("[Supervisor] Manual start triggered for '%s'", name)
	return nil
}

// StopDaemon stops a specific daemon manually.
func (s *Supervisor) StopDaemon(name string) error {
	s.lock.Lock()
	daemon, exists := s.Daemons[name]
	if !exists {
		s.lock.Unlock()
		return fmt.Errorf("daemon '%s' not found", name)
	}
	
	if daemon.Cancel == nil {
		s.lock.Unlock()
		return fmt.Errorf("daemon '%s' is not running", name)
	}
	
	cancelFunc := daemon.Cancel
	daemon.Cancel = nil
	s.lock.Unlock()

	cancelFunc()
	log.Printf("[Supervisor] Manual stop triggered for '%s'", name)
	return nil
}

// GetStatus returns a map of all daemons and their running status.
func (s *Supervisor) GetStatus() map[string]interface{} {
	s.lock.Lock()
	defer s.lock.Unlock()
	
	statusMap := make(map[string]interface{})
	for name, d := range s.Daemons {
		isRunning := d.Cancel != nil
		
		pid := -1
		if isRunning {
			d.lock.Lock()
			if d.cmdInstance != nil && d.cmdInstance.Process != nil {
				pid = d.cmdInstance.Process.Pid
			}
			d.lock.Unlock()
		}
		
		statusMap[name] = map[string]interface{}{
			"running":      isRunning,
			"pid":          pid,
			"auto_restart": d.AutoRestart,
			"auto_start":   d.AutoStart,
		}
	}
	return statusMap
}

// watchdog supervises a single daemon and handles restarts.
func (s *Supervisor) watchdog(d *ManagedDaemon) {
	for {
		err := s.runProcess(d)

		// Check if we were cancelled (clean shutdown)
		if d.ctx.Err() != nil {
			log.Printf("[Supervisor] Daemon '%s' stopped cleanly.", d.Name)
			// Ensure Cancel is set to nil when stopped
			d.lock.Lock()
			d.Cancel = nil
			d.lock.Unlock()
			return
		}

		if !d.AutoRestart {
			log.Printf("[Supervisor] Daemon '%s' exited (auto-restart disabled).", d.Name)
			return
		}

		d.RestartCount++
		if d.RestartCount > d.MaxRestarts {
			log.Printf("[Supervisor] Daemon '%s' exceeded max restarts (%d). Giving up.", d.Name, d.MaxRestarts)
			return
		}

		backoff := d.BackoffBase * time.Duration(d.RestartCount)
		log.Printf("[Supervisor] Daemon '%s' crashed (err: %v). Restarting in %v (Attempt %d/%d)", d.Name, err, backoff, d.RestartCount, d.MaxRestarts)
		
		select {
		case <-time.After(backoff):
		case <-d.ctx.Done():
			return
		}
	}
}

func (s *Supervisor) runProcess(d *ManagedDaemon) error {
	d.lock.Lock()
	cmd := exec.CommandContext(d.ctx, d.Cmd[0], d.Cmd[1:]...)
	cmd.Dir = d.Cwd
	
	// Inject DAEMON_MANAGER_OWNED=1 so python scripts know they are supervised
	env := os.Environ()
	env = append(env, "DAEMON_MANAGER_OWNED=1")
	cmd.Env = env
	
	// Route stdout/stderr to standard logger for now.
	// In production, we can write these to C:\AI-BS\logs.
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Start()
	if err != nil {
		d.lock.Unlock()
		return fmt.Errorf("failed to start: %w", err)
	}

	// Write PID file
	pidStr := fmt.Sprintf("%d", cmd.Process.Pid)
	os.WriteFile(d.pidFilePath, []byte(pidStr), 0644)
	
	d.cmdInstance = cmd
	d.lock.Unlock()

	log.Printf("[Supervisor] Daemon '%s' started with PID %d", d.Name, cmd.Process.Pid)

	err = cmd.Wait()

	// Clean up PID file on exit
	os.Remove(d.pidFilePath)

	return err
}
