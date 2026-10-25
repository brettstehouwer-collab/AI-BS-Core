//go:build !windows

package supervisor

import (
	"fmt"
	"os/exec"
)

type processIdentity struct {
	CreationFiletime string
	Executable       string
}

func inspectProcess(pid int) (processIdentity, error) {
	return processIdentity{}, fmt.Errorf("process handoff is supported only on Windows")
}
func configureProcess(cmd *exec.Cmd) {}
