# P77 - Normal player companion input diagnostic

Status: FAILED complete normal-input matrix; VERIFIED narrow saved Wait and offline reader repair.

The first normal Persistent Play run sent F7 immediately after ready, committed no event and timed out. Production companion choices require grounded BS; this suggests startup settling but does not prove the first failure cause. The second run waited two real seconds after owned-window activation. Its actual HUD showed Adam waiting and SAVED visible/durable 1. Normal clean shutdown reports revision/sequence 1. The test still timed out because its SQLite reader decoded the eight-byte heads as little endian. Production gameplay_store.cpp lines 51-52 encodes/decodes big endian. The value 1 was incorrectly read as 72057594037927936.

Both failed attempts and all logs remain. The two-strike native retry limit has been reached: no third native run was made. A corrected, unexecuted normal-play recipe uses big endian. Offline execution of definitions only checks nine integer boundary cases and the retained read-only database against actual shutdown metadata: revision 1, sequence 1, one event, Follow false. Database bytes are unchanged. This does not retrospectively pass either run or prove Follow, Recall, F9 or restart.

Both owned Windows Jobs drained to zero active processes without termination. No OS foreground forcing, global input, product code, installed player/shaders, SDK, family media or existing user save was changed. The source and private test chapters still match their exact initial inventory. The whole goal remains incomplete.

Next task: review the corrected recipe and offline counter evidence before any new native run. Use a fresh owned slot/report directory; retain the Persistent Play destructive-proof guard. Capture HUD before actions, allow ordinary startup settling, require four exact events, unchanged unrelated components, no repeated-Wait event and exact F9/new-process state. Do not treat these automated messages as human pacing or FPS acceptance.

Evidence: D:/AI-BS-Game-Resources/P77/Normal106CompanionInput. Corrected recipe: P77_normal_player_corrected_reader.py (also preserved in this checkpoint). Family source media and all SQLite databases are excluded from the software archive.
