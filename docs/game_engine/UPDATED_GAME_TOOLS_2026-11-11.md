# Updated AI-BS game tools — November 11, 2026

## Current testing launcher — November 21, 2026

**Current testing build — Studio 5.329.173, Workshop.7.1.** The recorded tour checks that it can walk back from the diagnostic panel and gives the player time to land after releasing forward input. Pick up the relay assembly at the sampled path contact and install it at the service socket to take the bypass. [Workshop.7.1 launcher](../../Launch-AI-BS-173-Workshop-Corridor-Qualified.cmd) · [Walkthrough checks](../../backups/workshop_corridor_20261121_v01/handoff.md). In Game Development, choose **Open Warm Beginning**, open or create the chapter, then select **Play saved chapter**. Press **F1** for controls.

Open **AI-BS Latest Candidate (Testing)** on the Administrator desktop to launch the current testing build. The compact play view shows the interaction, next objective, Adam's hint and save status. Press **F1** for full controls and recorded outcomes, then **F1** to return. [Gameplay HUD and walkthrough](../../backups/workshop_hud_20261121_v01/handoff.md) Follow the on-screen distance and turn directions to the diagnostic probe. When the centre prompt says **Collect diagnostic probe**, press **E**. Sample the supply contact, then the path contact. After saving, point at either contact to read the capacity, isolation setting and feed it recorded. [Contact readings and save checks](../../backups/workshop_readings_20261121_v01/handoff.md) In Game Development, select **Open Warm Beginning** → **Create First Boot opening**, choose a parent folder and a new folder name, then select **Play saved chapter**. The packaged Studio created a disposable chapter with all six asset packs and reopened the same revision-0 save. The separate **AI-BS Game Development** desktop shortcut selects **5.329.144**. [Testing launcher](../../Launch-AI-BS-Latest-Candidate.cmd) · [Workshop verification](../../backups/frozen_workshop_20261121_v01/handoff.md)

For a five-minute performance review, open **AI-BS Workshop Performance**. It starts the same packaged player at 1920 × 1080 in a fresh review save. Follow either route toward the shelter and Pencil Room. The timer starts after warmup and requires the game or its reading panel to stay in front. To review another published Workshop, drop its project folder onto the launcher. After the game closes, the console shows the folder containing the timing assessment and GPU-memory readings. [Performance launcher](../../Launch-AI-BS-Workshop-Performance.cmd) · [Verification and limits](../../backups/workshop_performance_20261121_v01/handoff.md)

The testing shortcut opened the Game Development screen in Studio 5.329.173. **Launch durable First Boot world (PC / DX12)** started the bundled player with a fresh save. After a controlled repair, a second launch restored revision 1 and showed the recorded Core Node 01 repair on the HUD. Both players and Studio closed normally. The test used a disposable Windows profile. [Game Development screen](../../backups/native173_game_entry_20261121_v01/run-203bf3f0/receipt.json) · [Save and reopen receipt](../../backups/native173_firstboot_action_20261121_v01/run-c7cc7705/receipt.json)

For an existing authored Workshop chapter, select **Open Warm Beginning**, **Open project**, choose the project directory, then select **Play saved chapter**. In a newly created chapter the **F7** command asks Adam to wait. A controlled test closed the player after the HUD showed saved revision 1. Opening **Play saved chapter** again restored Adam's waiting status and that same save. Folder selection was tested with the bundled Qt picker. [Saved action receipt](../../backups/workshop_progress_20261121_v01/fw-71cb086b-verified.json) · [Workshop opening](../../backups/native173_firstboot_action_20261121_v01/warm-handoff.md)

For BS-Chat, open **Launch-AI-BS-BS-Chat-Testing**. In this testing build Windows identifies the message box as **Message Stehouwer** even when it is empty. The label stays available while you type and after you clear your draft. [Dedicated BS-Chat testing launcher](../../Launch-AI-BS-BS-Chat-Testing.cmd) · [Windows accessibility check](../../backups/bschat_accessible_name_20261121_v01/acceptance/acceptance.json).

The long-term goal is active. The retained November 11 checkpoint below describes that date. In packaged Studio, open **BS-Chat → Toggle Split View → Syntax** to check Python syntax. Studio restored the exact scratchpad text after closing and reopening in a disposable profile. A separate check also restored an unsent message. [Packaged chat and scratchpad verification](../../backups/native173_bschat_syntax_20261121_v02/complete.md)

## November 11 packaging checkpoint

The long-term program was paused at this checkpoint. The packaging, launcher and backup work had separate authorization.

Double-click **AI-BS Game Development** on the current Administrator desktop, or run `C:\AI-BS\Launch-AI-BS-Game-Development.cmd`.
It opens Studio **5.329.144** directly at Game Engine Build. The tabs are **Build progress**, **Creator**, **Chapter creator** and **Assets**. Chapter creator is the route for opening an authored project and its preview/play controls. Keep existing authored projects together with their dependency files; this launcher does not replace or reset a save.

**AI-BS Work Controls** on the desktop, or `C:\AI-BS\Launch-AI-BS-Work-Controls.cmd`, opens batch controls, the terminal and local refactoring tools. These controls govern registered work in this Studio instance. Other services retain their own controls.

Both shortcuts target `C:\AI-BS\native_studio\releases\v5.329.144\AI_BS_Studio\AI_BS_Studio.exe`. The original `footb` desktop shortcuts and older releases remain preserved. The package is an unsigned engineering preview; it is not a declaration that the full game or every Studio subsystem is finished.

## Verified scope

- Current v02 package: 429 files, 216,156,156 bytes; static source/module/assets checks passed. Executable SHA-256: `cf2ba3743058769e4c593871a535dd8f80772435713fcc2008ee36d1d2d5db34`.
- Normal frozen `--game-development` startup visibly opened the game workspace at the current 1265×660 window size and closed normally. No project or existing save was opened by that check.
- The work-controls launcher opened the packaged controls. Its actual child version check passed with exit 0, version 5.329.144 and no metadata drift; the queue returned to idle. The window was left open after user input.
- Controlled v01 creator editing/save/fresh reopen, four DX12 viewports and saved-player lifecycle passed. V02 changes only five startup-entry lines across 182 staged inputs. The unchanged implementation evidence is retained; a complete new v02 gameplay or model run is not claimed.
- Firebase static dashboard 5.329.144 is live at [AI-BS Dashboard](https://ai-bs-dashboard.web.app/). The checked public version/index/main JavaScript matched the build; all 816 existing media hashes were preserved. Hosted static qualification is separate from native tools and authenticated workflows.

## Saved history and recovery

[Recovery source history](../architecture/AI_BS_RECOVERY_SOURCE_HISTORY_2026-11-11.md) records the supplied local roots, original profile and Drive locations, including sensitive folder references. A reference does not mean its contents were inspected or copied. Your ongoing shared [BS game folder](https://drive.google.com/drive/folders/1siuY6PGT0MFtfzFN6SWsgtgTyhHt9d6m) is the requested destination; its existing sharing is preserved.

The current source/log checkpoint, handoff and separately packaged clean runtime have their own file manifests and Drive verification receipts. Original saves, private databases, manuscripts, credentials and entire user profiles are not swept into the source/log archive. Old releases and private backup receipts remain available locally.

## Work retained for a future explicit resume

Authenticated creative edit/save/reopen/export, ordinary human pacing, checked captions, Adam likeness, signing, clean-machine qualification, full hosted/native parity and the unresolved Nsight capture gate remain separate. No manual gameplay test is requested. Follow `docs/agent_sync/current_long_term_goal.json` and the latest `docs/CODEX_HANDOFF.md` entry before resuming.
