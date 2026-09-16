package main

import (
	"bufio"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"strings"
	"sync"
	"syscall"
	"time"
	"unsafe"
)

// Win32 API Definitions
var (
	kernel32 = syscall.NewLazyDLL("kernel32.dll")
	user32   = syscall.NewLazyDLL("user32.dll")

	procOpenProcess          = kernel32.NewProc("OpenProcess")
	procCloseHandle          = kernel32.NewProc("CloseHandle")
	procReadProcessMemory    = kernel32.NewProc("ReadProcessMemory")
	procWriteProcessMemory   = kernel32.NewProc("WriteProcessMemory")
	procVirtualQueryEx       = kernel32.NewProc("VirtualQueryEx")
	procCreateToolhelp32Snap = kernel32.NewProc("CreateToolhelp32Snapshot")
	procProcess32FirstW      = kernel32.NewProc("Process32FirstW")
	procProcess32NextW       = kernel32.NewProc("Process32NextW")

	procGetAsyncKeyState = user32.NewProc("GetAsyncKeyState")
)

const (
	PROCESS_ALL_ACCESS        = 0x1F0FFF
	PROCESS_VM_READ           = 0x0010
	PROCESS_VM_WRITE          = 0x0020
	PROCESS_VM_OPERATION      = 0x0008
	PROCESS_QUERY_INFORMATION = 0x0400

	MEM_COMMIT = 0x1000

	PAGE_READWRITE         = 0x04
	PAGE_WRITECOPY         = 0x08
	PAGE_EXECUTE_READWRITE = 0x40
	PAGE_EXECUTE_WRITECOPY = 0x80

	PAGE_GUARD    = 0x100
	PAGE_NOACCESS = 0x01

	TH32CS_SNAPPROCESS = 0x00000002
)

type MemoryBasicInformation64 struct {
	BaseAddress       uint64
	AllocationBase    uint64
	AllocationProtect uint32
	Alignment1        uint32
	RegionSize        uint64
	State             uint32
	Protect           uint32
	Type              uint32
	Alignment2        uint32
}

type ProcessEntry32W struct {
	Size            uint32
	Usage           uint32
	ProcessID       uint32
	DefaultHeapID   uintptr
	ModuleID        uint32
	Threads         uint32
	ParentProcessID uint32
	PriClassBase    int32
	Flags           uint32
	ExeFile         [260]uint16
}

// BTD6MemoryEngine manages Win32 process memory operations
type BTD6MemoryEngine struct {
	mu          sync.Mutex
	pid         uint32
	hProcess    uintptr
	attached    bool
	processName string

	// Verified Locked Addresses
	cashAddresses  []uintptr
	livesAddresses []uintptr
	coinsAddresses []uintptr

	// Filter Candidate Tracking
	cashCandidates  []uintptr
	livesCandidates []uintptr
	coinsCandidates []uintptr

	// Target Freeze Values
	frozenCashVal  float64
	frozenLivesVal float64
	frozenCoinsVal int32

	// Cheat Feature States
	unlimitedCashEnabled     bool
	unlimitedLivesEnabled    bool
	unlimitedCoinsEnabled    bool
	zeroCostPlacementEnabled bool
	instantCooldownEnabled   bool

	// Scan Buffer (2MB pre-allocated)
	scanBuffer []byte
}

func NewBTD6MemoryEngine() *BTD6MemoryEngine {
	return &BTD6MemoryEngine{
		processName:    "BloonsTD6.exe",
		frozenCashVal:  99999.0,
		frozenLivesVal: 99999.0,
		frozenCoinsVal: 99999,
		scanBuffer:     make([]byte, 2*1024*1024),
	}
}

// Win32 API Helpers
func (e *BTD6MemoryEngine) FindProcessID(name string) uint32 {
	snapshot, _, _ := procCreateToolhelp32Snap.Call(TH32CS_SNAPPROCESS, 0)
	if snapshot == uintptr(syscall.InvalidHandle) {
		return 0
	}
	defer procCloseHandle.Call(snapshot)

	var entry ProcessEntry32W
	entry.Size = uint32(unsafe.Sizeof(entry))

	ret, _, _ := procProcess32FirstW.Call(snapshot, uintptr(unsafe.Pointer(&entry)))
	targetLower := strings.ToLower(name)

	for ret != 0 {
		exeName := strings.ToLower(syscall.UTF16ToString(entry.ExeFile[:]))
		if exeName == targetLower || strings.TrimSuffix(exeName, ".exe") == targetLower {
			return entry.ProcessID
		}
		ret, _, _ = procProcess32NextW.Call(snapshot, uintptr(unsafe.Pointer(&entry)))
	}
	return 0
}

func (e *BTD6MemoryEngine) Attach(pid uint32) bool {
	e.mu.Lock()
	defer e.mu.Unlock()

	if e.attached && e.pid == pid {
		return true
	}
	if e.hProcess != 0 {
		procCloseHandle.Call(e.hProcess)
		e.hProcess = 0
		e.attached = false
	}

	h, _, _ := procOpenProcess.Call(
		PROCESS_VM_READ|PROCESS_VM_WRITE|PROCESS_VM_OPERATION|PROCESS_QUERY_INFORMATION,
		0,
		uintptr(pid),
	)
	if h == 0 {
		h, _, _ = procOpenProcess.Call(PROCESS_ALL_ACCESS, 0, uintptr(pid))
	}
	if h == 0 {
		return false
	}

	e.pid = pid
	e.hProcess = h
	e.attached = true

	// Verify preset addresses for instant zero-latency locking
	presetCash := []uintptr{0x18de8408443, 0x18f983dd2e3}
	var validCash []uintptr
	for _, addr := range presetCash {
		val, err := e.readDoubleLocked(addr)
		if err == nil && val >= 0.0 && val < 100000000.0 {
			validCash = append(validCash, addr)
		}
	}
	if len(validCash) > 0 {
		e.cashAddresses = validCash
	}

	return true
}

func (e *BTD6MemoryEngine) Detach() {
	e.mu.Lock()
	defer e.mu.Unlock()

	if e.hProcess != 0 {
		procCloseHandle.Call(e.hProcess)
		e.hProcess = 0
	}
	e.attached = false
	e.pid = 0
}

func (e *BTD6MemoryEngine) IsAlive() bool {
	e.mu.Lock()
	defer e.mu.Unlock()
	if !e.attached || e.hProcess == 0 {
		return false
	}
	var exitCode uint32
	ret, _, _ := kernel32.NewProc("GetExitCodeProcess").Call(e.hProcess, uintptr(unsafe.Pointer(&exitCode)))
	return ret != 0 && exitCode == 259 // STILL_ACTIVE
}

func (e *BTD6MemoryEngine) ReadBytes(addr uintptr, buf []byte) (int, error) {
	if !e.attached || e.hProcess == 0 {
		return 0, fmt.Errorf("not attached")
	}
	var bytesRead uintptr
	ret, _, err := procReadProcessMemory.Call(
		e.hProcess,
		addr,
		uintptr(unsafe.Pointer(&buf[0])),
		uintptr(len(buf)),
		uintptr(unsafe.Pointer(&bytesRead)),
	)
	if ret == 0 {
		return 0, err
	}
	return int(bytesRead), nil
}

func (e *BTD6MemoryEngine) WriteBytes(addr uintptr, buf []byte) (int, error) {
	if !e.attached || e.hProcess == 0 {
		return 0, fmt.Errorf("not attached")
	}
	var bytesWritten uintptr
	ret, _, err := procWriteProcessMemory.Call(
		e.hProcess,
		addr,
		uintptr(unsafe.Pointer(&buf[0])),
		uintptr(len(buf)),
		uintptr(unsafe.Pointer(&bytesWritten)),
	)
	if ret == 0 {
		return 0, err
	}
	return int(bytesWritten), nil
}

func (e *BTD6MemoryEngine) readDoubleLocked(addr uintptr) (float64, error) {
	var buf [8]byte
	var bytesRead uintptr
	ret, _, err := procReadProcessMemory.Call(
		e.hProcess,
		addr,
		uintptr(unsafe.Pointer(&buf[0])),
		8,
		uintptr(unsafe.Pointer(&bytesRead)),
	)
	if ret == 0 || bytesRead != 8 {
		return 0, err
	}
	bits := binary.LittleEndian.Uint64(buf[:])
	return math.Float64frombits(bits), nil
}

func (e *BTD6MemoryEngine) ReadDouble(addr uintptr) (float64, error) {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.readDoubleLocked(addr)
}

func (e *BTD6MemoryEngine) WriteDouble(addr uintptr, val float64) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	var buf [8]byte
	binary.LittleEndian.PutUint64(buf[:], math.Float64bits(val))
	var bytesWritten uintptr
	ret, _, err := procWriteProcessMemory.Call(
		e.hProcess,
		addr,
		uintptr(unsafe.Pointer(&buf[0])),
		8,
		uintptr(unsafe.Pointer(&bytesWritten)),
	)
	if ret == 0 || bytesWritten != 8 {
		return err
	}
	return nil
}

func (e *BTD6MemoryEngine) ReadInt32(addr uintptr) (int32, error) {
	e.mu.Lock()
	defer e.mu.Unlock()
	var buf [4]byte
	var bytesRead uintptr
	ret, _, err := procReadProcessMemory.Call(
		e.hProcess,
		addr,
		uintptr(unsafe.Pointer(&buf[0])),
		4,
		uintptr(unsafe.Pointer(&bytesRead)),
	)
	if ret == 0 || bytesRead != 4 {
		return 0, err
	}
	return int32(binary.LittleEndian.Uint32(buf[:])), nil
}

func (e *BTD6MemoryEngine) WriteInt32(addr uintptr, val int32) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	var buf [4]byte
	binary.LittleEndian.PutUint32(buf[:], uint32(val))
	var bytesWritten uintptr
	ret, _, err := procWriteProcessMemory.Call(
		e.hProcess,
		addr,
		uintptr(unsafe.Pointer(&buf[0])),
		4,
		uintptr(unsafe.Pointer(&bytesWritten)),
	)
	if ret == 0 || bytesWritten != 4 {
		return err
	}
	return nil
}

// Memory Scanner with Natural Alignment & Overlap
func (e *BTD6MemoryEngine) scanExactDoubleAligned(target float64, maxMatches int, alignment int) []uintptr {
	var matches []uintptr
	if !e.attached || e.hProcess == 0 {
		return matches
	}

	targetBits := math.Float64bits(target)
	var address uint64 = 0
	maxAddress := uint64(0x7FFFFFFFFFFF)
	var mbi MemoryBasicInformation64
	mbiSize := uintptr(unsafe.Sizeof(mbi))

	chunkSize := len(e.scanBuffer)
	valLen := 8

	for address < maxAddress {
		ret, _, _ := procVirtualQueryEx.Call(
			e.hProcess,
			uintptr(address),
			uintptr(unsafe.Pointer(&mbi)),
			mbiSize,
		)
		if ret == 0 {
			address += 0x10000 // 64KB step
			continue
		}

		base := mbi.BaseAddress
		size := mbi.RegionSize
		nextAddress := base + size
		if nextAddress <= address {
			address += 0x10000
			continue
		}

		// Filter committed read/write pages without guard/noaccess
		isValid := (mbi.State == MEM_COMMIT) &&
			((mbi.Protect & (PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)) != 0) &&
			((mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS)) == 0)

		if isValid && size > 0 {
			curRegionAddr := base
			remaining := size

			for remaining >= uint64(valLen) {
				readLen := chunkSize
				if uint64(readLen) > remaining {
					readLen = int(remaining)
				}

				var bytesRead uintptr
				r, _, _ := procReadProcessMemory.Call(
					e.hProcess,
					uintptr(curRegionAddr),
					uintptr(unsafe.Pointer(&e.scanBuffer[0])),
					uintptr(readLen),
					uintptr(unsafe.Pointer(&bytesRead)),
				)

				actual := int(bytesRead)
				if r != 0 && actual >= valLen {
					for offset := 0; offset <= actual-valLen; offset++ {
						addr := uintptr(curRegionAddr) + uintptr(offset)
						if addr%uintptr(alignment) != 0 {
							continue
						}
						chunkBits := binary.LittleEndian.Uint64(e.scanBuffer[offset : offset+8])
						if chunkBits == targetBits {
							matches = append(matches, addr)
							if len(matches) >= maxMatches {
								return matches
							}
						}
					}
					overlap := valLen - 1
					if actual > overlap {
						curRegionAddr += uint64(actual - overlap)
						remaining -= uint64(actual - overlap)
					} else {
						break
					}
				} else {
					break
				}
			}
		}
		address = nextAddress
	}

	return matches
}

func (e *BTD6MemoryEngine) ScanExactDouble(target float64, maxMatches int) []uintptr {
	e.mu.Lock()
	defer e.mu.Unlock()

	// Try 8-byte alignment first
	matches := e.scanExactDoubleAligned(target, maxMatches, 8)
	if len(matches) == 0 {
		// Fallback to 4-byte alignment for packed IL2CPP structs
		matches = e.scanExactDoubleAligned(target, maxMatches, 4)
	}
	return matches
}

func (e *BTD6MemoryEngine) ScanExactInt32(target int32, maxMatches int) []uintptr {
	e.mu.Lock()
	defer e.mu.Unlock()

	var matches []uintptr
	if !e.attached || e.hProcess == 0 {
		return matches
	}

	targetBits := uint32(target)
	var address uint64 = 0
	maxAddress := uint64(0x7FFFFFFFFFFF)
	var mbi MemoryBasicInformation64
	mbiSize := uintptr(unsafe.Sizeof(mbi))

	chunkSize := len(e.scanBuffer)
	valLen := 4

	for address < maxAddress {
		ret, _, _ := procVirtualQueryEx.Call(
			e.hProcess,
			uintptr(address),
			uintptr(unsafe.Pointer(&mbi)),
			mbiSize,
		)
		if ret == 0 {
			address += 0x10000
			continue
		}

		base := mbi.BaseAddress
		size := mbi.RegionSize
		nextAddress := base + size
		if nextAddress <= address {
			address += 0x10000
			continue
		}

		isValid := (mbi.State == MEM_COMMIT) &&
			((mbi.Protect & (PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)) != 0) &&
			((mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS)) == 0)

		if isValid && size > 0 {
			curRegionAddr := base
			remaining := size

			for remaining >= uint64(valLen) {
				readLen := chunkSize
				if uint64(readLen) > remaining {
					readLen = int(remaining)
				}

				var bytesRead uintptr
				r, _, _ := procReadProcessMemory.Call(
					e.hProcess,
					uintptr(curRegionAddr),
					uintptr(unsafe.Pointer(&e.scanBuffer[0])),
					uintptr(readLen),
					uintptr(unsafe.Pointer(&bytesRead)),
				)

				actual := int(bytesRead)
				if r != 0 && actual >= valLen {
					for offset := 0; offset <= actual-valLen; offset++ {
						addr := uintptr(curRegionAddr) + uintptr(offset)
						if addr%4 != 0 {
							continue
						}
						chunkBits := binary.LittleEndian.Uint32(e.scanBuffer[offset : offset+4])
						if chunkBits == targetBits {
							matches = append(matches, addr)
							if len(matches) >= maxMatches {
								return matches
							}
						}
					}
					overlap := valLen - 1
					if actual > overlap {
						curRegionAddr += uint64(actual - overlap)
						remaining -= uint64(actual - overlap)
					} else {
						break
					}
				} else {
					break
				}
			}
		}
		address = nextAddress
	}

	return matches
}

// Multi-Stage Candidate Filtering & Auto-Probe Pipeline
func (e *BTD6MemoryEngine) AutoScanCash(targetVal *float64) []uintptr {
	if !e.attached || e.hProcess == 0 {
		return nil
	}
	if targetVal != nil && *targetVal > 0 {
		e.FirstScanCash(*targetVal)
		e.mu.Lock()
		defer e.mu.Unlock()
		return e.cashAddresses
	}

	// Probe standard starting values (Standard + Double Cash variants)
	candidates := []float64{
		650.0, 1300.0,  // Normal
		850.0, 1700.0,  // Easy
		450.0, 900.0,   // Hard
		1000.0, 2000.0, // Medium
		200.0, 400.0,   // Sandbox
		1750.0, 3500.0, // Deflation
		99999.0, 999999.0,
	}

	for _, val := range candidates {
		matches := e.ScanExactDouble(val, 200)
		if len(matches) > 0 && len(matches) <= 16 {
			e.mu.Lock()
			e.cashCandidates = matches
			e.cashAddresses = matches
			e.frozenCashVal = val
			e.mu.Unlock()
			sendLog("info", fmt.Sprintf("Auto-Scan Cash locked %d address(es) for $%.0f", len(matches), val))
			return matches
		}
	}
	return nil
}

func (e *BTD6MemoryEngine) AutoScanLives(targetVal *float64) []uintptr {
	if !e.attached || e.hProcess == 0 {
		return nil
	}
	if targetVal != nil && *targetVal > 0 {
		matches := e.ScanExactDouble(*targetVal, 200)
		if len(matches) > 0 {
			e.mu.Lock()
			e.livesCandidates = matches
			if len(matches) <= 16 {
				e.livesAddresses = matches
				e.frozenLivesVal = 99999.0
			}
			e.mu.Unlock()
			return matches
		}
	}

	candidates := []float64{200.0, 150.0, 100.0, 250.0, 1.0, 99999.0}
	for _, val := range candidates {
		matches := e.ScanExactDouble(val, 200)
		if len(matches) > 0 && len(matches) <= 16 {
			e.mu.Lock()
			e.livesCandidates = matches
			e.livesAddresses = matches
			e.frozenLivesVal = 99999.0
			e.mu.Unlock()
			sendLog("info", fmt.Sprintf("Auto-Scan Lives locked %d address(es) for %.0f hearts", len(matches), val))
			return matches
		}
	}
	return nil
}

func (e *BTD6MemoryEngine) FirstScanCash(val float64) int {
	matches := e.ScanExactDouble(val, 2000)
	e.mu.Lock()
	defer e.mu.Unlock()

	e.cashCandidates = matches
	if len(matches) > 0 && len(matches) <= 16 {
		e.cashAddresses = matches
		e.frozenCashVal = val
	}
	return len(matches)
}

func (e *BTD6MemoryEngine) NextScanCash(newVal float64) int {
	e.mu.Lock()
	if len(e.cashCandidates) == 0 {
		if len(e.cashAddresses) > 0 {
			e.cashCandidates = e.cashAddresses
		} else {
			e.mu.Unlock()
			return e.FirstScanCash(newVal)
		}
	}

	var filtered []uintptr
	for _, addr := range e.cashCandidates {
		cur, err := e.readDoubleLocked(addr)
		if err == nil && math.Abs(cur-newVal) < 0.001 {
			filtered = append(filtered, addr)
		}
	}

	if len(filtered) > 0 {
		e.cashCandidates = filtered
		if len(filtered) <= 16 {
			e.cashAddresses = filtered
			e.frozenCashVal = newVal
		}
	}
	defer e.mu.Unlock()
	return len(filtered)
}

func (e *BTD6MemoryEngine) FirstScanLives(val float64) int {
	matches := e.ScanExactDouble(val, 2000)
	e.mu.Lock()
	defer e.mu.Unlock()

	e.livesCandidates = matches
	if len(matches) > 0 && len(matches) <= 16 {
		e.livesAddresses = matches
		e.frozenLivesVal = 99999.0
	}
	return len(matches)
}

func (e *BTD6MemoryEngine) NextScanLives(newVal float64) int {
	e.mu.Lock()
	if len(e.livesCandidates) == 0 {
		if len(e.livesAddresses) > 0 {
			e.livesCandidates = e.livesAddresses
		} else {
			e.mu.Unlock()
			return e.FirstScanLives(newVal)
		}
	}

	var filtered []uintptr
	for _, addr := range e.livesCandidates {
		cur, err := e.readDoubleLocked(addr)
		if err == nil && math.Abs(cur-newVal) < 0.001 {
			filtered = append(filtered, addr)
		}
	}

	if len(filtered) > 0 {
		e.livesCandidates = filtered
		if len(filtered) <= 16 {
			e.livesAddresses = filtered
			e.frozenLivesVal = 99999.0
		}
	}
	defer e.mu.Unlock()
	return len(filtered)
}

func (e *BTD6MemoryEngine) FirstScanCoins(val int32) int {
	matches := e.ScanExactInt32(val, 2000)
	if len(matches) == 0 {
		// Modern BTD6 stores Monkey Money as double (float64)
		dMatches := e.ScanExactDouble(float64(val), 2000)
		if len(dMatches) > 0 {
			matches = dMatches
		}
	}
	e.mu.Lock()
	defer e.mu.Unlock()

	e.coinsCandidates = matches
	if len(matches) > 0 && len(matches) <= 16 {
		e.coinsAddresses = matches
		e.frozenCoinsVal = val
	}
	return len(matches)
}

func (e *BTD6MemoryEngine) NextScanCoins(newVal int32) int {
	e.mu.Lock()
	defer e.mu.Unlock()

	if len(e.coinsCandidates) == 0 {
		return 0
	}

	var filtered []uintptr
	var buf [8]byte
	targetD := float64(newVal)
	for _, addr := range e.coinsCandidates {
		var bytesRead uintptr
		ret, _, _ := procReadProcessMemory.Call(
			e.hProcess,
			addr,
			uintptr(unsafe.Pointer(&buf[0])),
			8,
			uintptr(unsafe.Pointer(&bytesRead)),
		)
		if ret != 0 {
			if bytesRead >= 4 {
				curI := int32(binary.LittleEndian.Uint32(buf[:4]))
				if curI == newVal {
					filtered = append(filtered, addr)
					continue
				}
			}
			if bytesRead == 8 {
				curD := math.Float64frombits(binary.LittleEndian.Uint64(buf[:8]))
				if math.Abs(curD-targetD) < 0.001 {
					filtered = append(filtered, addr)
					continue
				}
			}
		}
	}

	if len(filtered) > 0 {
		e.coinsCandidates = filtered
		if len(filtered) <= 16 {
			e.coinsAddresses = filtered
			e.frozenCoinsVal = newVal
		}
	}
	return len(filtered)
}

func (e *BTD6MemoryEngine) AddCash(amount float64) bool {
	e.mu.Lock()
	targets := e.cashAddresses
	if len(targets) == 0 && len(e.cashCandidates) > 0 && len(e.cashCandidates) <= 16 {
		targets = e.cashCandidates
		e.cashAddresses = targets
	}
	e.mu.Unlock()

	if len(targets) == 0 {
		targets = e.AutoScanCash(nil)
		if len(targets) == 0 {
			return false
		}
	}

	e.mu.Lock()
	defer e.mu.Unlock()
	for _, addr := range targets {
		cur, err := e.readDoubleLocked(addr)
		if err == nil {
			var buf [8]byte
			newVal := cur + amount
			binary.LittleEndian.PutUint64(buf[:], math.Float64bits(newVal))
			var bytesWritten uintptr
			procWriteProcessMemory.Call(
				e.hProcess,
				addr,
				uintptr(unsafe.Pointer(&buf[0])),
				8,
				uintptr(unsafe.Pointer(&bytesWritten)),
			)
			e.frozenCashVal = newVal
		}
	}
	e.cashAddresses = targets
	return true
}

func (e *BTD6MemoryEngine) SetCoins(target int32) bool {
	e.mu.Lock()
	defer e.mu.Unlock()

	targets := e.coinsAddresses
	if len(targets) == 0 && len(e.coinsCandidates) > 0 && len(e.coinsCandidates) <= 16 {
		targets = e.coinsCandidates
	}
	e.frozenCoinsVal = target
	if len(targets) == 0 {
		return false
	}
	var buf [4]byte
	binary.LittleEndian.PutUint32(buf[:], uint32(target))
	for _, addr := range targets {
		var bytesWritten uintptr
		procWriteProcessMemory.Call(
			e.hProcess,
			addr,
			uintptr(unsafe.Pointer(&buf[0])),
			4,
			uintptr(unsafe.Pointer(&bytesWritten)),
		)
	}
	e.coinsAddresses = targets
	return true
}

// Tick Loop: 25ms freeze writes without scanning overhead
func (e *BTD6MemoryEngine) Tick() {
	e.mu.Lock()
	defer e.mu.Unlock()

	if !e.attached || e.hProcess == 0 {
		return
	}

	if e.unlimitedCashEnabled && len(e.cashAddresses) > 0 {
		var buf [8]byte
		binary.LittleEndian.PutUint64(buf[:], math.Float64bits(e.frozenCashVal))
		for _, addr := range e.cashAddresses {
			var bw uintptr
			procWriteProcessMemory.Call(e.hProcess, addr, uintptr(unsafe.Pointer(&buf[0])), 8, uintptr(unsafe.Pointer(&bw)))
		}
	}

	if e.unlimitedLivesEnabled && len(e.livesAddresses) > 0 {
		var buf [8]byte
		binary.LittleEndian.PutUint64(buf[:], math.Float64bits(e.frozenLivesVal))
		for _, addr := range e.livesAddresses {
			var bw uintptr
			procWriteProcessMemory.Call(e.hProcess, addr, uintptr(unsafe.Pointer(&buf[0])), 8, uintptr(unsafe.Pointer(&bw)))
		}
	}

	if e.unlimitedCoinsEnabled && len(e.coinsAddresses) > 0 {
		var buf [4]byte
		binary.LittleEndian.PutUint32(buf[:], uint32(e.frozenCoinsVal))
		for _, addr := range e.coinsAddresses {
			var bw uintptr
			procWriteProcessMemory.Call(e.hProcess, addr, uintptr(unsafe.Pointer(&buf[0])), 4, uintptr(unsafe.Pointer(&bw)))
		}
	}
}

// JSON IPC Protocol Messages
type CommandMessage struct {
	Action   string   `json:"action"`
	Value    *float64 `json:"value,omitempty"`
	Amount   *float64 `json:"amount,omitempty"`
	Feature  string   `json:"feature,omitempty"`
	Variable string   `json:"variable,omitempty"`
}

type StateUpdateMessage struct {
	Type                 string                 `json:"type"`
	Status               string                 `json:"status"`
	PID                  uint32                 `json:"pid"`
	CashLocked           bool                   `json:"cash_locked"`
	CashAddresses        []string               `json:"cash_addresses"`
	CashCandidatesCount  int                    `json:"cash_candidates_count"`
	LivesLocked          bool                   `json:"lives_locked"`
	LivesAddresses       []string               `json:"lives_addresses"`
	LivesCandidatesCount int                    `json:"lives_candidates_count"`
	CoinsLocked          bool                   `json:"coins_locked"`
	CoinsAddresses       []string               `json:"coins_addresses"`
	CoinsCandidatesCount int                    `json:"coins_candidates_count"`
	Features             map[string]interface{} `json:"features"`
	Variables            map[string]interface{} `json:"variables"`
}

type LogMessage struct {
	Type    string `json:"type"`
	Level   string `json:"level"`
	Message string `json:"message"`
}

func sendJSON(v interface{}) {
	data, err := json.Marshal(v)
	if err == nil {
		fmt.Println(string(data))
	}
}

func sendLog(level, msg string) {
	sendJSON(LogMessage{
		Type:    "log",
		Level:   level,
		Message: msg,
	})
}

func main() {
	engine := NewBTD6MemoryEngine()
	sendLog("info", "BTD6 Native Go Memory Daemon v5.252.0 Initialized")

	// 25ms Tick Freeze Loop
	go func() {
		ticker := time.NewTicker(25 * time.Millisecond)
		for range ticker.C {
			engine.Tick()
		}
	}()

	// Global Win32 Hotkey Poller (GetAsyncKeyState)
	go func() {
		keyMap := []struct {
			vk     uintptr
			action string
		}{
			{0x70, "f1"},  // VK_F1
			{0x61, "f1"},  // VK_NUMPAD1
			{0x71, "f2"},  // VK_F2
			{0x62, "f2"},  // VK_NUMPAD2
			{0x72, "f3"},  // VK_F3
			{0x63, "f3"},  // VK_NUMPAD3
			{0x76, "f7"},  // VK_F7
			{0x67, "f7"},  // VK_NUMPAD7
			{0x79, "f10"}, // VK_F10
			{0x60, "f10"}, // VK_NUMPAD0
		}

		pressed := make(map[uintptr]bool)
		ticker := time.NewTicker(40 * time.Millisecond)

		for range ticker.C {
			if !engine.attached {
				continue
			}

			for _, km := range keyMap {
				ret, _, _ := procGetAsyncKeyState.Call(km.vk)
				isDown := (ret & 0x8000) != 0

				if isDown && !pressed[km.vk] {
					pressed[km.vk] = true
					switch km.action {
					case "f1":
						engine.mu.Lock()
						engine.unlimitedCashEnabled = !engine.unlimitedCashEnabled
						active := engine.unlimitedCashEnabled
						addrsCount := len(engine.cashAddresses)
						engine.mu.Unlock()
						if active && addrsCount == 0 {
							engine.AutoScanCash(nil)
						}
						sendLog("info", fmt.Sprintf("[HOTKEY] Unlimited Match Cash: %v", active))

					case "f2":
						engine.mu.Lock()
						engine.unlimitedLivesEnabled = !engine.unlimitedLivesEnabled
						active := engine.unlimitedLivesEnabled
						addrsCount := len(engine.livesAddresses)
						engine.mu.Unlock()
						if active && addrsCount == 0 {
							engine.AutoScanLives(nil)
						}
						sendLog("info", fmt.Sprintf("[HOTKEY] Unlimited Lives: %v", active))

					case "f3":
						if engine.AddCash(50000.0) {
							sendLog("info", "[HOTKEY] Injected +$50,000 Cash")
						} else {
							sendLog("warn", "[HOTKEY] Add cash failed: no cash addresses locked")
						}

					case "f7":
						engine.mu.Lock()
						engine.unlimitedCoinsEnabled = !engine.unlimitedCoinsEnabled
						active := engine.unlimitedCoinsEnabled
						engine.mu.Unlock()
						sendLog("info", fmt.Sprintf("[HOTKEY] Unlimited Monkey Money: %v", active))

					case "f10":
						engine.mu.Lock()
						engine.unlimitedCashEnabled = false
						engine.unlimitedLivesEnabled = false
						engine.unlimitedCoinsEnabled = false
						engine.zeroCostPlacementEnabled = false
						engine.instantCooldownEnabled = false
						engine.mu.Unlock()
						sendLog("info", "[HOTKEY] Emergency Reset: All cheats deactivated")
					}
				} else if !isDown && pressed[km.vk] {
					pressed[km.vk] = false
				}
			}
		}
	}()

	// 1-Second Process Auto-Detection & Watchdog Loop
	go func() {
		ticker := time.NewTicker(1 * time.Second)
		for range ticker.C {
			if !engine.attached {
				pid := engine.FindProcessID("BloonsTD6.exe")
				if pid != 0 {
					if err := engine.Attach(pid); err {
						sendLog("info", fmt.Sprintf("Attached to BloonsTD6.exe (PID: %d)", pid))
						// Background auto-calibration probe
						go func() {
							time.Sleep(500 * time.Millisecond)
							engine.AutoScanCash(nil)
							engine.AutoScanLives(nil)
						}()
					}
				}
			} else {
				if !engine.IsAlive() {
					sendLog("warn", "BloonsTD6.exe has terminated. Detaching memory engine.")
					engine.Detach()
				}
			}

			// Broadcast state update
			engine.mu.Lock()
			attached := engine.attached
			pid := engine.pid

			var cashStrs []string
			for _, a := range engine.cashAddresses {
				cashStrs = append(cashStrs, fmt.Sprintf("0x%X", a))
			}
			var livesStrs []string
			for _, a := range engine.livesAddresses {
				livesStrs = append(livesStrs, fmt.Sprintf("0x%X", a))
			}
			var coinsStrs []string
			for _, a := range engine.coinsAddresses {
				coinsStrs = append(coinsStrs, fmt.Sprintf("0x%X", a))
			}

			status := "SEARCHING"
			if attached {
				status = "ATTACHED"
			}

			features := map[string]interface{}{
				"Unlimited Match Cash":   engine.unlimitedCashEnabled,
				"Unlimited Lives":        engine.unlimitedLivesEnabled,
				"Unlimited Monkey Money": engine.unlimitedCoinsEnabled,
				"Add $50k Cash":          "READY",
				"Zero-Cost Placement":    engine.zeroCostPlacementEnabled,
				"Instant Cooldowns":      engine.instantCooldownEnabled,
				"Reset & Restore":        "READY",
			}

			variables := map[string]interface{}{
				"frozen_cash_val":  engine.frozenCashVal,
				"frozen_lives_val": engine.frozenLivesVal,
				"frozen_coins_val": engine.frozenCoinsVal,
			}

			state := StateUpdateMessage{
				Type:                 "state_update",
				Status:               status,
				PID:                  pid,
				CashLocked:           len(engine.cashAddresses) > 0,
				CashAddresses:        cashStrs,
				CashCandidatesCount:  len(engine.cashCandidates),
				LivesLocked:          len(engine.livesAddresses) > 0,
				LivesAddresses:       livesStrs,
				LivesCandidatesCount: len(engine.livesCandidates),
				CoinsLocked:          len(engine.coinsAddresses) > 0,
				CoinsAddresses:       coinsStrs,
				CoinsCandidatesCount: len(engine.coinsCandidates),
				Features:             features,
				Variables:            variables,
			}
			engine.mu.Unlock()

			sendJSON(state)
		}
	}()

	// Read commands from standard input
	scanner := bufio.NewScanner(os.Stdin)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}

		var cmd CommandMessage
		if err := json.Unmarshal([]byte(line), &cmd); err != nil {
			sendJSON(map[string]string{"type": "error", "message": "Malformed JSON command: " + err.Error()})
			continue
		}

		switch cmd.Action {
		case "auto_calibrate", "auto_scan":
			cMatches := engine.AutoScanCash(cmd.Value)
			lMatches := engine.AutoScanLives(nil)
			sendLog("info", fmt.Sprintf("Auto-Calibrate Complete: %d cash addresses, %d lives addresses locked", len(cMatches), len(lMatches)))

		case "first_scan_cash":
			val := 650.0
			if cmd.Value != nil {
				val = *cmd.Value
			}
			count := engine.FirstScanCash(val)
			sendLog("info", fmt.Sprintf("First Scan Cash ($%.1f): Found %d candidates", val, count))

		case "next_scan_cash":
			if cmd.Value == nil {
				sendJSON(map[string]string{"type": "error", "message": "next_scan_cash requires value"})
				continue
			}
			count := engine.NextScanCash(*cmd.Value)
			sendLog("info", fmt.Sprintf("Next Scan Cash ($%.1f): Filtered to %d candidates", *cmd.Value, count))

		case "lock_cash":
			engine.mu.Lock()
			if len(engine.cashCandidates) > 0 && len(engine.cashAddresses) == 0 {
				engine.cashAddresses = engine.cashCandidates
			}
			if cmd.Value != nil {
				engine.frozenCashVal = *cmd.Value
			}
			engine.unlimitedCashEnabled = true
			cnt := len(engine.cashAddresses)
			engine.mu.Unlock()
			sendLog("info", fmt.Sprintf("Locked Cash to $%.0f across %d address(es)", engine.frozenCashVal, cnt))

		case "add_cash":
			amt := 50000.0
			if cmd.Amount != nil {
				amt = *cmd.Amount
			}
			if engine.AddCash(amt) {
				sendLog("info", fmt.Sprintf("Added $%.0f match cash", amt))
			} else {
				sendLog("warn", "Cannot add cash: No cash addresses locked (run First Scan or Auto-Calibrate)")
			}

		case "first_scan_lives":
			val := 200.0
			if cmd.Value != nil {
				val = *cmd.Value
			}
			count := engine.FirstScanLives(val)
			sendLog("info", fmt.Sprintf("First Scan Lives (%.0f): Found %d candidates", val, count))

		case "next_scan_lives":
			if cmd.Value == nil {
				sendJSON(map[string]string{"type": "error", "message": "next_scan_lives requires value"})
				continue
			}
			count := engine.NextScanLives(*cmd.Value)
			sendLog("info", fmt.Sprintf("Next Scan Lives (%.0f): Filtered to %d candidates", *cmd.Value, count))

		case "lock_lives":
			engine.mu.Lock()
			if len(engine.livesCandidates) > 0 && len(engine.livesAddresses) == 0 {
				engine.livesAddresses = engine.livesCandidates
			}
			if cmd.Value != nil {
				engine.frozenLivesVal = *cmd.Value
			} else {
				engine.frozenLivesVal = 99999.0
			}
			engine.unlimitedLivesEnabled = true
			cnt := len(engine.livesAddresses)
			engine.mu.Unlock()
			sendLog("info", fmt.Sprintf("Locked Lives to %.0f across %d address(es)", engine.frozenLivesVal, cnt))

		case "first_scan_coins":
			val := int32(99999)
			if cmd.Value != nil {
				val = int32(*cmd.Value)
			}
			count := engine.FirstScanCoins(val)
			sendLog("info", fmt.Sprintf("First Scan Coins (%d): Found %d candidates", val, count))

		case "next_scan_coins":
			if cmd.Value == nil {
				sendJSON(map[string]string{"type": "error", "message": "next_scan_coins requires value"})
				continue
			}
			count := engine.NextScanCoins(int32(*cmd.Value))
			sendLog("info", fmt.Sprintf("Next Scan Coins (%d): Filtered to %d candidates", int32(*cmd.Value), count))

		case "set_coins":
			val := int32(99999)
			if cmd.Value != nil {
				val = int32(*cmd.Value)
			}
			if engine.SetCoins(val) {
				sendLog("info", fmt.Sprintf("Set Monkey Money to %d", val))
			} else {
				sendLog("warn", "Set coins pending: No coins addresses locked")
			}

		case "toggle_feature":
			engine.mu.Lock()
			switch cmd.Feature {
			case "Unlimited Match Cash":
				engine.unlimitedCashEnabled = !engine.unlimitedCashEnabled
				active := engine.unlimitedCashEnabled
				addrsCount := len(engine.cashAddresses)
				engine.mu.Unlock()
				if active && addrsCount == 0 {
					engine.AutoScanCash(nil)
				}
				engine.mu.Lock()
				sendLog("info", fmt.Sprintf("Unlimited Match Cash: %v", engine.unlimitedCashEnabled))

			case "Unlimited Lives":
				engine.unlimitedLivesEnabled = !engine.unlimitedLivesEnabled
				active := engine.unlimitedLivesEnabled
				addrsCount := len(engine.livesAddresses)
				engine.mu.Unlock()
				if active && addrsCount == 0 {
					engine.AutoScanLives(nil)
				}
				engine.mu.Lock()
				sendLog("info", fmt.Sprintf("Unlimited Lives: %v", engine.unlimitedLivesEnabled))

			case "Unlimited Monkey Money":
				engine.unlimitedCoinsEnabled = !engine.unlimitedCoinsEnabled
				sendLog("info", fmt.Sprintf("Unlimited Monkey Money: %v", engine.unlimitedCoinsEnabled))

			case "Add $50k Cash":
				engine.mu.Unlock()
				engine.AddCash(50000.0)
				engine.mu.Lock()

			case "Zero-Cost Placement":
				engine.zeroCostPlacementEnabled = !engine.zeroCostPlacementEnabled
				sendLog("info", fmt.Sprintf("Zero-Cost Placement: %v", engine.zeroCostPlacementEnabled))

			case "Instant Cooldowns":
				engine.instantCooldownEnabled = !engine.instantCooldownEnabled
				sendLog("info", fmt.Sprintf("Instant Cooldowns: %v", engine.instantCooldownEnabled))

			case "Reset & Restore":
				engine.unlimitedCashEnabled = false
				engine.unlimitedLivesEnabled = false
				engine.unlimitedCoinsEnabled = false
				engine.zeroCostPlacementEnabled = false
				engine.instantCooldownEnabled = false
				sendLog("info", "All cheats disabled and reset to normal")
			}
			engine.mu.Unlock()

		case "set_variable":
			engine.mu.Lock()
			if cmd.Value != nil {
				switch cmd.Variable {
				case "frozen_cash_val":
					engine.frozenCashVal = *cmd.Value
					sendLog("info", fmt.Sprintf("Updated frozen_cash_val = %.1f", engine.frozenCashVal))
				case "frozen_lives_val":
					engine.frozenLivesVal = *cmd.Value
					sendLog("info", fmt.Sprintf("Updated frozen_lives_val = %.1f", engine.frozenLivesVal))
				case "frozen_coins_val":
					engine.frozenCoinsVal = int32(*cmd.Value)
					sendLog("info", fmt.Sprintf("Updated frozen_coins_val = %d", engine.frozenCoinsVal))
				}
			}
			engine.mu.Unlock()

		case "quit":
			sendLog("info", "Shutting down Go daemon...")
			engine.Detach()
			os.Exit(0)
		}
	}
}
