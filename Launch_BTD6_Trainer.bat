@echo off
title AI-BS Standalone Bloons TD 6 Trainer
cd /d "C:\AI-BS"
echo =================================================================
echo        AI-BS STANDALONE GAME TRAINER: BLOONS TD 6
echo =================================================================
echo  Quick Keys (Dual-Bound):
echo    F1  / NUMPAD 1 : Unlimited Match Cash ($99,999.0)
echo    F2  / NUMPAD 2 : Unlimited Match Lives (99,999.0)
echo    F3  / NUMPAD 3 : Add $50,000 Match Cash (One-Shot)
echo    F4  / NUMPAD 4 : Zero-Cost Tower Placement
echo    F5  / NUMPAD 5 : Instant Ability Cooldowns
echo    F6             : Toggle On-Screen Transparent HUD Overlay
echo    F7  / NUMPAD 7 : Unlimited Monkey Money (99,999 Coins Freeze)
echo    F10 / NUMPAD 0 : Reset ^& Restore Normal State
echo =================================================================
echo  Starting Engine ^& Interactive HUD Overlay...
echo  Tip: Use the HUD to Launch the game, Prepare memory, and click cheats!
python "game_trainer\launch_btd6_trainer.py"
pause
