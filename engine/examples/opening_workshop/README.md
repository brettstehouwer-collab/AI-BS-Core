# Opening Workshop: installed SDK0.15 example

This small generated SDK demonstration uses public installed headers and CMake
exports. It creates a new session, builds the optional Workshop draft without
assets, validates five owned fixtures, roundtrips AIBD3, saves a new authoring
journal and reopens it through a new owner with the same fingerprint.

It also finds a grounded, locally visible probe approach with the public CPU
collision API. The chapter action and public Workshop rule must agree on an
owned probe collection plan. That plan is never committed to the authoring
document or injected into saved gameplay progress.

Build against an installed SDK0.15 prefix; the exact version is required:

```powershell
cmake -S C:/AI-BS/engine/examples/opening_workshop -B D:/AI-BS-Game-Resources/Examples/OpeningWorkshopRelease -G "Visual Studio 17 2022" -A x64 -DCMAKE_PREFIX_PATH=D:/AI-BS-Game-Resources/SDK/0.15.0/release
cmake --build D:/AI-BS-Game-Resources/Examples/OpeningWorkshopRelease --config Release --parallel 2
D:/AI-BS-Game-Resources/Examples/OpeningWorkshopRelease/Release/opening_workshop_example.exe D:/AI-BS-Game-Resources/Examples/MyNewWorkshop
```

The output parent directory must exist. Existing outputs are refused, including
an empty directory. Use a fresh path for each run. Failed staging directories
are preserved for diagnosis. Successful output contains `chapter.aiba`,
`opening.aibd` and `example.json`; these are standalone SDK sample artifacts.
The report records the fingerprint and deliberately limited verification scope.

For Debug, select an installed Debug SDK prefix and build with `--config Debug`.
`installed-sdk-Release.txt` or `installed-sdk-Debug.txt` in the build directory
records the header prefix and actual imported libraries.

No renderer, window, family recording, external asset, AI inference or network
service is used. This is a CPU integration example, not a full chapter runtime,
gameplay-save, human walkthrough or pacing measurement. Use the Creator/factory
workflow for a complete chapter project and keep existing projects separate.
