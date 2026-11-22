#pragma once

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <vector>
#include <string>
#include <sstream>
#include <iostream>
#include <cstdint>

/**
 * AI-BS Game Trainer Suite: Native C++ Win32 Memory Engine
 * Header-only external memory manipulation utility.
 */

namespace Trainer {

    struct MemoryPatch {
        uintptr_t address;
        std::vector<uint8_t> originalBytes;
        std::vector<uint8_t> patchedBytes;
        bool isApplied;
    };

    class MemoryEngine {
    public:
        HANDLE hProcess = nullptr;
        DWORD processId = 0;
        uintptr_t moduleBase = 0;
        std::string processName;
        std::vector<MemoryPatch> activePatches;

        MemoryEngine() = default;
        ~MemoryEngine() { Detach(); }

        bool Attach(const std::string& exeName) {
            processName = exeName;
            processId = FindProcessId(exeName);
            if (!processId) return false;

            hProcess = OpenProcess(PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION, FALSE, processId);
            if (!hProcess) return false;

            moduleBase = GetModuleBaseAddress(processId, exeName);
            return true;
        }

        void Detach() {
            for (auto& patch : activePatches) {
                if (patch.isApplied) {
                    WriteBytes(patch.address, patch.originalBytes, true);
                    patch.isApplied = false;
                }
            }
            activePatches.clear();

            if (hProcess) {
                CloseHandle(hProcess);
                hProcess = nullptr;
            }
            processId = 0;
            moduleBase = 0;
        }

        bool IsAlive() const {
            if (!hProcess) return false;
            DWORD exitCode = 0;
            if (GetExitCodeProcess(hProcess, &exitCode)) {
                return exitCode == STILL_ACTIVE;
            }
            return false;
        }

        // -------------------------------------------------------------
        // Primitives
        // -------------------------------------------------------------

        std::vector<uint8_t> ReadBytes(uintptr_t address, size_t size) {
            std::vector<uint8_t> buffer(size);
            SIZE_T bytesRead = 0;
            if (ReadProcessMemory(hProcess, reinterpret_cast<LPCVOID>(address), buffer.data(), size, &bytesRead)) {
                buffer.resize(bytesRead);
                return buffer;
            }
            return {};
        }

        bool WriteBytes(uintptr_t address, const std::vector<uint8_t>& data, bool unprotect = false) {
            DWORD oldProtect = 0;
            if (unprotect) {
                VirtualProtectEx(hProcess, reinterpret_cast<LPVOID>(address), data.size(), PAGE_EXECUTE_READWRITE, &oldProtect);
            }

            SIZE_T bytesWritten = 0;
            BOOL success = WriteProcessMemory(hProcess, reinterpret_cast<LPVOID>(address), data.data(), data.size(), &bytesWritten);

            if (unprotect && oldProtect) {
                DWORD temp = 0;
                VirtualProtectEx(hProcess, reinterpret_cast<LPVOID>(address), data.size(), oldProtect, &temp);
            }

            return success && (bytesWritten == data.size());
        }

        template <typename T>
        T Read(uintptr_t address) {
            T value{};
            SIZE_T bytesRead = 0;
            ReadProcessMemory(hProcess, reinterpret_cast<LPCVOID>(address), &value, sizeof(T), &bytesRead);
            return value;
        }

        template <typename T>
        bool Write(uintptr_t address, const T& value) {
            SIZE_T bytesWritten = 0;
            return WriteProcessMemory(hProcess, reinterpret_cast<LPVOID>(address), &value, sizeof(T), &bytesWritten) && (bytesWritten == sizeof(T));
        }

        // -------------------------------------------------------------
        // Multi-level Pointer Resolution
        // -------------------------------------------------------------

        uintptr_t ResolvePointerChain(uintptr_t baseAddress, const std::vector<ptrdiff_t>& offsets) {
            uintptr_t current = baseAddress;
            for (size_t i = 0; i < offsets.size() - 1; ++i) {
                current = Read<uintptr_t>(current + offsets[i]);
                if (!current) return 0; // Null pointer
            }
            return current + offsets.back();
        }

        // -------------------------------------------------------------
        // Patching & NOPing
        // -------------------------------------------------------------

        bool Patch(uintptr_t address, const std::vector<uint8_t>& newBytes) {
            std::vector<uint8_t> original = ReadBytes(address, newBytes.size());
            if (original.size() != newBytes.size()) return false;

            if (WriteBytes(address, newBytes, true)) {
                activePatches.push_back({ address, original, newBytes, true });
                return true;
            }
            return false;
        }

        bool NOP(uintptr_t address, size_t count) {
            std::vector<uint8_t> nops(count, 0x90);
            return Patch(address, nops);
        }

        // -------------------------------------------------------------
        // Internal Helpers
        // -------------------------------------------------------------

        static DWORD FindProcessId(const std::string& processName) {
            HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
            if (hSnap == INVALID_HANDLE_VALUE) return 0;

            PROCESSENTRY32 pe;
            pe.dwSize = sizeof(PROCESSENTRY32);
            DWORD pid = 0;

            if (Process32First(hSnap, &pe)) {
                do {
                    if (processName == pe.szExeFile) {
                        pid = pe.th32ProcessID;
                        break;
                    }
                } while (Process32Next(hSnap, &pe));
            }
            CloseHandle(hSnap);
            return pid;
        }

        static uintptr_t GetModuleBaseAddress(DWORD pid, const std::string& moduleName) {
            HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
            if (hSnap == INVALID_HANDLE_VALUE) return 0;

            MODULEENTRY32 me;
            me.dwSize = sizeof(MODULEENTRY32);
            uintptr_t baseAddr = 0;

            if (Module32First(hSnap, &me)) {
                do {
                    if (moduleName == me.szModule) {
                        baseAddr = reinterpret_cast<uintptr_t>(me.modBaseAddr);
                        break;
                    }
                } while (Module32Next(hSnap, &me));
            }
            CloseHandle(hSnap);
            return baseAddr;
        }
    };
}
