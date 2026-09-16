package main

import (
	"archive/zip"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

var (
	targetDir   = flag.String("target-dir", "", "Target directory containing the application to update")
	payloadZip  = flag.String("payload-zip", "", "Path to the downloaded zip archive containing the update files")
	parentPID   = flag.Int("parent-pid", 0, "PID of the calling parent process to wait for termination")
	executable  = flag.String("executable", "AI-BS Sovereign Studio.exe", "Executable name to launch after update completes")
	backup      = flag.Bool("backup", true, "Create a backup directory before overwriting files")
	timeoutSec  = flag.Int("timeout", 20, "Seconds to wait for parent process exit before force-kill")
	dryRun      = flag.Bool("dry-run", false, "Test mode without writing files")
	logFile     = flag.String("log-file", "", "Optional log file path")
	launchAfter = flag.Bool("relaunch", true, "Relaunch the updated executable after completion")
)

func initLogging() *os.File {
	path := *logFile
	if path == "" {
		localApp := os.Getenv("LOCALAPPDATA")
		if localApp != "" {
			dir := filepath.Join(localApp, "AI_BS_Studio", "updates")
			os.MkdirAll(dir, 0755)
			path = filepath.Join(dir, "aibs_updater.log")
		} else {
			path = "aibs_updater.log"
		}
	}
	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err == nil {
		log.SetOutput(io.MultiWriter(os.Stdout, f))
	}
	return f
}

func isProcessRunning(pid int) bool {
	if pid <= 0 {
		return false
	}
	// On Windows, use OpenProcess with PROCESS_QUERY_LIMITED_INFORMATION (0x1000)
	handle, err := syscall.OpenProcess(0x1000, false, uint32(pid))
	if err != nil {
		return false
	}
	defer syscall.CloseHandle(handle)

	var exitCode uint32
	err = syscall.GetExitCodeProcess(handle, &exitCode)
	if err != nil {
		return false
	}
	// 259 is STILL_ACTIVE
	return exitCode == 259
}

func waitForProcessExit(pid int, timeout time.Duration) error {
	if pid <= 0 {
		return nil
	}
	deadline := time.Now().Add(timeout)
	log.Printf("[Updater] Waiting for parent process (PID: %d) to terminate...\n", pid)

	for time.Now().Before(deadline) {
		if !isProcessRunning(pid) {
			log.Printf("[Updater] Parent process (PID: %d) has exited.\n", pid)
			return nil
		}
		time.Sleep(250 * time.Millisecond)
	}

	log.Printf("[Updater] Timeout reached waiting for PID %d. Attempting force termination...\n", pid)
	cmd := exec.Command("taskkill", "/F", "/T", "/PID", fmt.Sprintf("%d", pid))
	_ = cmd.Run()
	time.Sleep(500 * time.Millisecond)

	if isProcessRunning(pid) {
		return fmt.Errorf("process PID %d refused to exit", pid)
	}
	log.Printf("[Updater] Parent process (PID: %d) terminated.\n", pid)
	return nil
}

func killLingeringEcosystemProcesses() {
	// Terminate any stranded background engine helpers that hold locks in target directory
	processes := []string{"aibs_engine.exe", "brain_backend.exe"}
	for _, proc := range processes {
		cmd := exec.Command("taskkill", "/F", "/IM", proc)
		_ = cmd.Run()
	}
	time.Sleep(300 * time.Millisecond)
}

func sanitizeZipPath(targetDir, filePath string) (string, error) {
	dest := filepath.Join(targetDir, filepath.Clean(filePath))
	// Prevent Zip-Slip directory traversal vulnerability
	rel, err := filepath.Rel(targetDir, dest)
	if err != nil || strings.HasPrefix(rel, "..") {
		return "", fmt.Errorf("illegal file path in archive: %s", filePath)
	}
	return dest, nil
}

func extractZipPayload(zipPath, destDir, backupDir string) error {
	r, err := zip.OpenReader(zipPath)
	if err != nil {
		return fmt.Errorf("failed to open zip file: %w", err)
	}
	defer r.Close()

	log.Printf("[Updater] Extracting %d items from update payload: %s\n", len(r.File), zipPath)

	for _, f := range r.File {
		targetPath, err := sanitizeZipPath(destDir, f.Name)
		if err != nil {
			log.Printf("[Updater] Warning: %v (skipping)\n", err)
			continue
		}

		if f.FileInfo().IsDir() {
			if !*dryRun {
				if err := os.MkdirAll(targetPath, f.Mode()); err != nil {
					return fmt.Errorf("failed to create directory %s: %w", targetPath, err)
				}
			}
			continue
		}

		// Ensure parent directory exists
		if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
			return fmt.Errorf("failed to create parent directory for %s: %w", targetPath, err)
		}

		// Create backup if target file exists
		if *backup && backupDir != "" {
			if _, err := os.Stat(targetPath); err == nil {
				relPath, _ := filepath.Rel(destDir, targetPath)
				backupFilePath := filepath.Join(backupDir, relPath)
				os.MkdirAll(filepath.Dir(backupFilePath), 0755)
				_ = copyFile(targetPath, backupFilePath)
			}
		}

		if *dryRun {
			log.Printf("[DryRun] Would write: %s (%d bytes)\n", targetPath, f.UncompressedSize64)
			continue
		}

		// Retry loop for Windows file lock release
		var writeErr error
		for attempt := 1; attempt <= 5; attempt++ {
			writeErr = writeZipFile(f, targetPath)
			if writeErr == nil {
				break
			}
			log.Printf("[Updater] Retry %d/5 writing %s: %v\n", attempt, filepath.Base(targetPath), writeErr)
			time.Sleep(300 * time.Millisecond)
		}

		if writeErr != nil {
			return fmt.Errorf("failed writing %s after 5 attempts: %w", targetPath, writeErr)
		}
		log.Printf("[Updater] Updated: %s (%d bytes)\n", filepath.Base(targetPath), f.UncompressedSize64)
	}

	return nil
}

func writeZipFile(f *zip.File, destPath string) error {
	rc, err := f.Open()
	if err != nil {
		return err
	}
	defer rc.Close()

	// If destination file is locked, try renaming to .old first
	if _, err := os.Stat(destPath); err == nil {
		oldPath := destPath + ".old"
		_ = os.Remove(oldPath)
		_ = os.Rename(destPath, oldPath)
	}

	outFile, err := os.OpenFile(destPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
	if err != nil {
		return err
	}
	defer outFile.Close()

	_, err = io.Copy(outFile, rc)
	return err
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}

func relaunchApplication(targetDir, exeName string) error {
	exePath := filepath.Join(targetDir, exeName)
	if _, err := os.Stat(exePath); err != nil {
		return fmt.Errorf("executable not found at: %s", exePath)
	}

	log.Printf("[Updater] Relaunching application: %s\n", exePath)

	// Detached process flags on Windows
	cmd := exec.Command(exePath)
	cmd.Dir = targetDir
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: syscall.CREATE_NEW_PROCESS_GROUP | 0x00000008, // DETACHED_PROCESS
	}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start application: %w", err)
	}

	log.Printf("[Updater] Successfully launched updated application (New PID: %d).\n", cmd.Process.Pid)
	return nil
}

func main() {
	flag.Parse()
	logHandle := initLogging()
	if logHandle != nil {
		defer logHandle.Close()
	}

	log.Println("================================================================")
	log.Println("     AI-BS SOVEREIGN INTELLIGENCE - APP-LEVEL AUTO-UPDATER      ")
	log.Println("================================================================")

	if *targetDir == "" {
		// Default to current working directory
		cwd, err := os.Getwd()
		if err != nil {
			log.Fatalf("[Updater] Error resolving current directory: %v\n", err)
		}
		*targetDir = cwd
	}

	log.Printf("[Updater] Target Directory : %s\n", *targetDir)
	log.Printf("[Updater] Payload Zip File : %s\n", *payloadZip)
	log.Printf("[Updater] Target Executable: %s\n", *executable)

	if *payloadZip == "" {
		log.Fatalf("[Updater] Missing required argument: -payload-zip\n")
	}

	if _, err := os.Stat(*payloadZip); err != nil {
		log.Fatalf("[Updater] Payload zip file does not exist: %s\n", *payloadZip)
	}

	// 1. Wait for Parent PID to Exit
	if *parentPID > 0 {
		timeout := time.Duration(*timeoutSec) * time.Second
		if err := waitForProcessExit(*parentPID, timeout); err != nil {
			log.Fatalf("[Updater] Failed waiting for parent PID: %v\n", err)
		}
	}

	// 2. Clear any lingering child engine locks
	killLingeringEcosystemProcesses()

	// 3. Prepare Backup Directory
	var backupDir string
	if *backup && !*dryRun {
		timestamp := time.Now().Format("20060102_150405")
		backupDir = filepath.Join(*targetDir, fmt.Sprintf("_update_backup_%s", timestamp))
		if err := os.MkdirAll(backupDir, 0755); err != nil {
			log.Printf("[Updater] Warning: Failed to create backup directory: %v\n", err)
		} else {
			log.Printf("[Updater] Rollback backup prepared at: %s\n", backupDir)
		}
	}

	// 4. Extract and Overwrite Files
	log.Println("[Updater] Applying patch payload...")
	if err := extractZipPayload(*payloadZip, *targetDir, backupDir); err != nil {
		log.Printf("[Updater] CRITICAL ERROR applying update: %v\n", err)
		if backupDir != "" {
			log.Println("[Updater] Attempting automated rollback from backup...")
			// Rollback from backupDir to targetDir
			_ = filepath.Walk(backupDir, func(path string, info os.FileInfo, err error) error {
				if err == nil && !info.IsDir() {
					rel, _ := filepath.Rel(backupDir, path)
					dest := filepath.Join(*targetDir, rel)
					_ = copyFile(path, dest)
				}
				return nil
			})
			log.Println("[Updater] Rollback completed.")
		}
		log.Fatalf("[Updater] Update aborted due to extraction error.\n")
	}

	log.Println("[Updater] Update payload applied successfully.")

	// 5. Relaunch Application if requested
	if *launchAfter && !*dryRun {
		if err := relaunchApplication(*targetDir, *executable); err != nil {
			log.Printf("[Updater] Error relaunching application: %v\n", err)
		}
	}

	log.Println("[Updater] Update workflow complete. Exiting stub.")
}
