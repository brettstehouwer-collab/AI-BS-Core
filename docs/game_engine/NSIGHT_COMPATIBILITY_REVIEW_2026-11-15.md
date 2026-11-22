# Nsight compatibility review

Read-only review; no capture replay, injection, driver/settings change or guard edit.
Current local nvidia-smi reports RTX4090/driver621.24; installed Nsight is2026.4.0.
NVIDIA's current release notes require Windows driver620or newer and explicitly
describe Direct3D debug-runtime use as unsupported. The troubleshooting guide
also distinguishes release-runtime analysis from debug-runtime incompatibilities.
Sources: [NVIDIA release notes](https://docs.nvidia.com/nsight-graphics/ReleaseNotes/index.html),
[NVIDIA troubleshooting](https://docs.nvidia.com/nsight-graphics/UserGuide/troubleshooting.html).

The observed driver meets that stated version floor. This does not establish
that either retained1421error is fixed. The failed injected-debug captures,
unchanged engine debug guard and separately successful image replay remain as
recorded in NSIGHT_1421_REPRO_2026-11-11.md. No equivalent capture trial was run.

Planning correction: keep uninstrumented debug validation separate from supported
normal Release profiling. A future normal Release capture must use the engine's
existing normal policy, an independently pinned workload and its own acceptance
receipt. It cannot relabel the failed debug-injection lane or supply ordinary
gameplay/performance proof. Selecting such a lane is not an error-filter, global
debug/security change or authorization to rerun a stopped command. Exact workload
and capture admission remain to be selected; no new runtime qualification here.
