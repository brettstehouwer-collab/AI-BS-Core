# Windows Commands Reference for AI-BS Matrix

**Applies to:** Windows Server 2025, 2022, 2019, 2016, Windows 11, Windows 10, Azure Local 2311.2 and later.

All supported versions of Windows and Windows Server have a set of Win32 console commands built in. This document describes the Windows Commands used to automate tasks by using scripts or scripting tools.

## Command-line shells
Windows has two command-line shells: the **Command shell** and **PowerShell**. Each shell provides an environment to automate IT operations.

1. **Command shell:** The first shell built into Windows to automate routine tasks with batch (`.bat`) files. Scripts accept all commands that are available at the command line.
2. **PowerShell:** Designed to extend the capabilities of the Command shell to run PowerShell commands called cmdlets. Cmdlets provide a more extensible scripting language. You can run both Windows Commands and PowerShell cmdlets in PowerShell, but the Command shell can only run Windows Commands.

*Recommendation:* For the most robust, up-to-date Windows automation, PowerShell is recommended instead of Windows Commands or Windows Script Host.

## Command shell file and directory name automatic completion
The Command shell can automatically complete file and directory names when a specified control character is pressed (default is the tab key).

Settings are found in the registry:
- `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Command Processor\CompletionChar`
- `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Command Processor\PathCompletionChar`

You can enable or disable file and directory name completion per instance of a Command shell by running `cmd.exe` with the parameter and switch `/F:ON` or `/F:OFF`.

## Command-line reference A-Z

### A
- active, add, add alias, add volume, adprep, append, arp, assign, assoc, at, atmadm, attach-vdisk, attrib, attributes, attributes disk, attributes volume, auditpol, auditpol backup, auditpol clear, auditpol get, auditpol list, auditpol remove, auditpol resourcesacl, auditpol restore, auditpol set, autochk, autoconv, autofmt, automount

### B
- bcdboot, bcdedit, bdehdcfg, bdehdcfg driveinfo, bdehdcfg newdriveletter, bdehdcfg quiet, bdehdcfg restart, bdehdcfg size, bdehdcfg target, begin backup, begin restore, bitsadmin, bitsadmin (various subcommands), bootcfg, break

### C
- cacls, call, cd, certreq, certutil, change, change logon, change port, change user, chcp, chdir, chglogon, chgport, chgusr, chkdsk, chkntfs, choice, cipher, clean, cleanmgr, clip, cls, cmd, cmdkey, cmstp, color, comp, compact, compact vdisk, convert, convert basic, convert dynamic, convert gpt, convert mbr, copy, create, create partition efi, create partition extended, create partition logical, create partition msr, create partition primary, create volume mirror, create volume raid, create volume simple, create volume stripe, cscript

### D
- date, dcdiag, dcgpofix, dcpromo, defrag, del, delete, delete disk, delete partition, delete shadows, delete volume, detach vdisk, detail, detail disk, detail partition, detail vdisk, detail volume, dfsdiag, dfsrmig, diantz, dir, diskcomp, diskcopy, diskpart, diskperf, diskraid, diskshadow, dispdiag, dnscmd, doskey, driverquery, dtrace

### E
- echo, edit, endlocal, end restore, erase, eventcreate, Evntcmd, exec, exit, expand, expand vdisk, expose, extend, extract

### F
- fc, filesystems, find, findstr, finger, flattemp, fondue, for, forfiles, format, freedisk, fsutil, fsutil (various subcommands), ftp, ftp (various subcommands), ftype, fveupdate

### G
- getmac, gettype, goto, gpfixup, gpresult, gpt, gpupdate, graftabl

### H
- help, helpctr, hostname

### I
- icacls, if, import (shadowdisk), import (diskpart), inactive, ipconfig, ipxroute, irftp

### J
- jetpack

### K
- klist, ksetup, ksetup (various subcommands), ktmutil, ktpass

### L
- label, list, list providers, list shadows, list writers, load metadata, lodctr, logman, logman (various subcommands), logoff, lpq, lpr

### M
- macfile, makecab, manage bde, manage bde (various subcommands), mapadmin, md, merge vdisk, mkdir, mklink, mmc, mode, more, mount, mountvol, move, mqbkup, mqsvc, mqtgsvc, msdt, msg, msiexec, msinfo32, mstsc

### N
- nbtstat, netcfg, netdom, netdom (various subcommands), net print, net user, netsh, netsh (various subcommands), netstat, nfsadmin, nfsshare, nfsstat, nlbmgr, nltest, nslookup, nslookup (various subcommands), ntbackup, ntcmdprompt, ntfrsutl

### O
- offline, offline disk, offline volume, online, online disk, online volume, openfiles

### P
- pagefileconfig, path, pathping, pause, pbadmin, pentnt, perfmon, ping, pktmon, pnpunattend, pnputil, popd, powershell, powershell ise, print, prncnfg, prndrvr, prnjobs, prnmngr, prnport, prnqctl, prompt, pubprn, pushd, pushprinterconnections, pwlauncher, pwsh

### Q
- qappsrv, qprocess, query, query process, query session, query termserver, query user, quser, qwinsta

### R
- rd, rdpsign, recover, recover disk group, refsutil, refsutil (various subcommands), reg, reg (various subcommands), regini, regsvr32, relog, rem, remove, ren, rename, repadmin, repair, repair bde, replace, rescan, reset, reset session, retain, revert, rexec, risetup, rmdir, robocopy, route ws2008, rpcinfo, rpcping, rsh, rundll32, rundll32 printui, rwinsta

### S
- san, sc config, sc create, sc delete, sc query, schtasks, scwcmd, scwcmd (various subcommands), secedit, secedit (various subcommands), select, select disk, select partition, select vdisk, select volume, serverceipoptin, servermanagercmd, serverweroptin, set environmental variables, set shadow copy, set context, set id, setlocal, set metadata, set option, set verbose, setspn, setx, sfc, shadow, shift, showmount, shrink, shutdown, simulate restore, sort, start, subcommand (various), subst, sxstrace, sysmon, sysocmgr, systeminfo

### T
- takeown, tapicfg, taskkill, tasklist, tcmsetup, telnet, telnet (various subcommands), tftp, time, timeout, title, tlntadmn, tpmtool, tpmvscmgr, tracerpt, tracert, tree, tscon, tsdiscon, tsecimp, tskill, tsprof, type, typeperf, tzutil

### U
- unexpose, uniqueid, unlodctr

### V
- ver, verifier, verify, vol, vssadmin, vssadmin delete shadows, vssadmin list shadows, vssadmin list writers, vssadmin resize shadowstorage

### W
- waitfor, wbadmin, wbadmin (various subcommands), wdsutil, wecutil, wevtutil, where, whoami, winnt, winnt32, winrs, winsat mem, winsat mfmedia, wmic, writer, wscript

### X
- xcopy
