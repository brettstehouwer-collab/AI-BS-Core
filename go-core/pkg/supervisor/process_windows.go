package supervisor

import (
	"fmt"
	"os/exec"
	"strconv"
	"syscall"
	"unsafe"
)

type processIdentity struct {
	CreationFiletime string
	Executable       string
}

func inspectProcess(pid int) (processIdentity, error) {
	var result processIdentity
	handle, err := syscall.OpenProcess(syscall.PROCESS_QUERY_INFORMATION|syscall.SYNCHRONIZE, false, uint32(pid))
	if err != nil {
		return result, err
	}
	defer syscall.CloseHandle(handle)
	status, err := syscall.WaitForSingleObject(handle, 0)
	if err != nil {
		return result, err
	}
	if status != syscall.WAIT_TIMEOUT {
		return result, fmt.Errorf("process %d is no longer running", pid)
	}
	var creation, exit, kernel, user syscall.Filetime
	if err = syscall.GetProcessTimes(handle, &creation, &exit, &kernel, &user); err != nil {
		return result, err
	}
	result.CreationFiletime = strconv.FormatUint(uint64(creation.HighDateTime)<<32|uint64(creation.LowDateTime), 10)
	buffer := make([]uint16, 32768)
	length := uint32(len(buffer))
	query := syscall.NewLazyDLL("kernel32.dll").NewProc("QueryFullProcessImageNameW")
	ok, _, callErr := query.Call(uintptr(handle), 0, uintptr(unsafe.Pointer(&buffer[0])), uintptr(unsafe.Pointer(&length)))
	if ok == 0 {
		return result, callErr
	}
	result.Executable = syscall.UTF16ToString(buffer[:length])
	return result, nil
}
func configureProcess(cmd *exec.Cmd) { cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true} }
