# **Windows Admin Terminal Commands Reference**

This guide lists the most critical command-line utilities used by system administrators to troubleshoot, secure, and manage Windows environments. It covers classic Command Prompt (cmd.exe) commands as well as their modern PowerShell equivalents.

## **1\. Network Diagnostics & Configuration**

Network commands are essential for identifying routing issues, DNS failures, active port listeners, and adapter configurations.

| Command | Category / Syntax | What It Does | Why Admins Use It |
| :---- | :---- | :---- | :---- |
| **ipconfig** | CMD / PowerShell | Displays current TCP/IP configuration. Useful switches: • /all (shows MAC address, DNS, DHCP details) • /flushdns (clears the local DNS resolver cache) • /release & /renew (drops and requests a new DHCP IP) | To diagnose IP conflicts, reset broken DHCP leases, and force local machines to fetch fresh DNS records after a domain change. |
| **ping** | CMD / PowerShell | Sends ICMP Echo Requests to verify local or remote network connectivity. Use \-t to ping continuously until stopped (Ctrl+C). | To verify if a remote host or local gateway is responsive on the network. |
| **Test-NetConnection** | PowerShell (tnc) | Modern replacement for ping and legacy port scanning tools. Example: Test-NetConnection \-ComputerName google.com \-Port 443 | To quickly test if a specific network port (like HTTPS, RDP, or SSH) is open through firewalls, which standard ping cannot do. |
| **tracert** | CMD | Traces the network path packets take to reach a destination. Use /d to bypass DNS lookups and speed up the trace. | To find the exact hop (router/gateway) where network traffic is dropping or experiencing severe latency. |
| **pathping** | CMD | A hybrid of ping and tracert. It traces the path, then pings each intermediate hop for a period to analyze packet loss. | To pinpoint slow or failing network equipment on a specific path without running separate ping tests. |
| **netstat** | CMD / PowerShell | Displays active TCP connections, listening ports, and Ethernet statistics. Use \-ano to display numerical addresses and process IDs (PIDs). | To identify rogue connections, check if a service is listening on its designated port, and find which process is using a blocked port. |
| **nslookup** | CMD / PowerShell | Queries DNS servers to resolve hostnames to IP addresses and vice-versa. | To verify if local DNS records are correct or if a remote domain name is resolving properly on the internet. |
| **arp \-a** | CMD | Displays the current ARP (Address Resolution Protocol) cache table, mapping IP addresses to physical MAC addresses. | To detect IP conflicts, verify local physical network paths, or locate unauthorized hardware on the subnet. |
| **netsh** | CMD / PowerShell | Legacy command-line scripting utility used to configure local network interfaces, firewalls, and wireless profiles. | To script static IP assignments, reset the TCP/IP stack (netsh int ip reset), or reset Windows Sockets (netsh winsock reset). |

## **2\. System Diagnostics, Integrity & Repair**

These commands target operating system health, corrupt system files, policy enforcement, and registry settings.

| Command | Category / Syntax | What It Does | Why Admins Use It |
| :---- | :---- | :---- | :---- |
| **DISM** | CMD / PowerShell | Deployment Image Servicing and Management. Example: dism /online /cleanup-image /restorehealth | To repair the local Windows Component Store (the source files used to install/repair Windows features) using Windows Update as a source. |
| **sfc /scannow** | CMD / PowerShell | System File Checker. Scans the integrity of all protected system files and replaces corrupted versions with cached originals. | To fix operating system instability, missing DLLs, or broken built-in tools by repairing critical files. |
| **systeminfo** | CMD / PowerShell | Pulls detailed hardware specs, operating system build, system boot time, BIOS version, and a list of installed hotfixes (Windows Updates). | To quickly audit a target machine's exact patch level, CPU architecture, and basic hardware parameters without utilizing a GUI. |
| **gpupdate /force** | CMD / PowerShell | Forces an immediate refresh of local and Active Directory Group Policies on the computer. | To ensure security configurations, desktop restrictions, or software deployments apply immediately rather than waiting for the standard 90-minute background cycle. |
| **gpresult /r** | CMD / PowerShell | Displays the Resultant Set of Policy (RSoP) for the logged-in user and computer. | To troubleshoot why a specific Group Policy Object (GPO) or restriction is not applying to a device or user. |
| **driverquery** | CMD / PowerShell | Generates a complete list of installed device drivers and their current state (running, stopped). | To identify outdated, broken, or rogue drivers causing Blue Screens of Death (BSOD) or hardware failures. |
| **w32tm** | CMD / PowerShell | Windows Time Service tool. Used to configure and diagnose time synchronization. Example: w32tm /resync | To fix time drifts on workstations. If a domain-joined machine's clock drifts more than 5 minutes from the Domain Controller, Active Directory authentication will fail. |

## **3\. Security, Permissions & User Management**

Managing access controls, system identities, and local user accounts directly from the terminal bypassing the settings app.

| Command | Category / Syntax | What It Does | Why Admins Use It |
| :---- | :---- | :---- | :---- |
| **whoami /all** | CMD / PowerShell | Displays the current user's name, security identifiers (SIDs), active security groups, and current privileges. | To check if a command prompt is successfully running with elevated administrator rights, and to troubleshoot access token problems. |
| **net user** | CMD / PowerShell | Manages local user accounts. Example: net user username password /add | To quickly reset forgotten passwords, unlock accounts, or create temporary administration credentials during recovery tasks. |
| **net localgroup** | CMD / PowerShell | Manages local groups. Example: net localgroup Administrators username /add | To elevate a standard user to a local administrator or assign permissions to locally defined security groups. |
| **icacls** | CMD / PowerShell | Displays or modifies Access Control Lists (ACLs) for files and directories. | To fix "Access Denied" errors, back up folder permissions, or apply inheritance properties across large file trees. |
| **takeown** | CMD / PowerShell | Forces an administrator to become the owner of a file or folder. Example: takeown /f C:\\Folder /r | To gain access to system files, user profiles left behind by deleted accounts, or folders locked by corrupt security contexts. |
| **cipher /w:C:\\** | CMD / PowerShell | Overwrites deleted data on a storage volume to prevent recovery. /w removes data from available unused disk space. | To securely sanitize a drive's free space before decommissioning a workstation or handing it to another user. |
| **runas** | CMD / PowerShell | Executes an application under the security context of a different user account. | To run administrative utilities while logged into a standard, non-privileged user account. |

## **4\. File System, Disks & Storage**

Managing partitioning tables, volume health, and massive data transfers cleanly.

| Command | Category / Syntax | What It Does | Why Admins Use It |
| :---- | :---- | :---- | :---- |
| **chkdsk** | CMD / PowerShell | Checks a volume for logical and physical errors. Use /f to fix errors and /r to scan for and recover bad sectors. | To recover RAW drives, repair corrupted NTFS structures, and identify failing mechanical drives or SSDs. |
| **diskpart** | CMD / PowerShell | Launches the command-line partition manager. Allows selection, deletion, formatting, and shrinking of physical volumes. | To clean read-only USB drives, wipe bad partition tables, convert MBR to GPT, or structure boot volumes outside of the standard GUI limits. |
| **robocopy** | CMD / PowerShell | Robust File Copy. A highly reliable, multi-threaded command-line file copy tool that handles interruption gracefully. | To migrate massive directory trees over unstable networks, preserve timestamps and NTFS permissions, and mirror directories reliably. |
| **fsutil** | CMD / PowerShell | File System Utility. Performs specialized tasks related to FAT and NTFS file systems. | To query file system parameters, manage sparse files, or create dummy files of specific sizes for testing disk capacity. |

## **5\. Process, Service & Automation Management**

Monitoring and terminating active tasks, configuring system background services, and controlling power states.

| Command | Category / Syntax | What It Does | Why Admins Use It |
| :---- | :---- | :---- | :---- |
| **tasklist** | CMD | Displays a list of all currently active processes, their PIDs, and memory usage. | To find unresponsive applications or hidden background processes without running Task Manager. |
| **taskkill** | CMD | Forcefully terminates processes. Use /IM for process names or /PID for numeric PIDs. Example: taskkill /IM outlook.exe /F | To terminate completely frozen, locked processes that refuse to close through standard means. |
| **sc** | CMD / PowerShell | Service Controller tool. Communicates with the Service Control Manager to start, stop, query, or configure background services. | To change a service's startup type (e.g., automatic, manual, disabled) or force-stop a service that is stuck in a "Stopping" state. |
| **schtasks** | CMD / PowerShell | Configures, deletes, queries, or runs scheduled tasks on local or remote computers. | To automate system maintenance, deploy background scripts, or audit tasks scheduled by third-party software. |
| **shutdown** | CMD / PowerShell | Triggers system shutdown, reboot, or logoff. Useful switches: • /r /t 0 (immediate restart) • /s /f (force shutdown of all apps) | To remotely reboot servers, schedule automatic restarts in maintenance windows, or initiate safe mode reboots. |

## **FORUM CONSENSUS & EMPIRICAL CORRELATION**

In communities like Reddit's r/sysadmin and various technical forums, administrators emphasize standard operational workflows and common pitfalls associated with these commands:

1. **The DISM/SFC Pipeline Order:** Experienced administrators notes that executing sfc /scannow on its own often fails if the local Windows recovery image is corrupted. The industry-standard sequence is to run dism /online /cleanup-image /restorehealth first. This ensures that the component store is fully verified and clean, which then allows sfc to successfully pull healthy source files to replace corrupted operating system files.  
2. **Modern PowerShell Replacement Over CMD Muscle Memory:** While legacy utilities like ping and telnet are deeply hardwired into system administrator workflows, modern networks frequently block standard ICMP ping traffic. The community strongly recommends using PowerShell's Test-NetConnection (tnc). It allows targeting specific ports, and returns structured objects rather than raw strings, making it easier to script and parse.  
3. **Robocopy Over Modern PowerShell alternatives:** Even in high-end PowerShell environments, administrators prefer the legacy C++ compiled robocopy executable over Copy-Item. Robocopy is significantly faster, uses less memory, supports aggressive multithreading (/MT), natively logs errors, and handles connection dropouts over corporate VPN links with automatic retry policies.