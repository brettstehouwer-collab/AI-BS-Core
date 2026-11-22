@echo off
title AI-BS YouTube Live Stream Ingest Launcher
color 0b

echo ===============================================================================
echo                AI-BS SOVEREIGN STUDIO - YOUTUBE LIVE LAUNCHER
echo ===============================================================================
echo  Target: rtmp://a.rtmp.youtube.com/live2
echo  Stream Key: je5p-8zxu-d7rj-d73s-cvu6
echo ===============================================================================
echo.
echo  [1] Live Desktop Broadcast (NVIDIA NVENC 1080p 60fps) -> YouTube Live
echo  [2] Multi-Stream Ingest (Local Nginx Relay -> YouTube + StehouwerPublishing.com)
echo  [3] Send 60-Second 1080p60 Test Pattern & Audio Tone -> YouTube Live
echo  [4] Launch OBS Studio (Pre-Configured with YouTube Stream Key)
echo  [5] Exit
echo.
set /p CHOICE=" Select streaming mode [1-5]: "

if "%CHOICE%"=="1" goto STREAM_DESKTOP_DIRECT
if "%CHOICE%"=="2" goto STREAM_MULTI_RELAY
if "%CHOICE%"=="3" goto STREAM_TEST_PATTERN
if "%CHOICE%"=="4" goto LAUNCH_OBS
if "%CHOICE%"=="5" exit /b 0

:STREAM_DESKTOP_DIRECT
echo.
echo [*] Starting Live Desktop Screen Broadcast to YouTube Live...
echo [*] Press Ctrl+C in this window or press 'q' to stop the stream.
echo.
ffmpeg -y -f gdigrab -framerate 60 -i desktop -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 -c:v h264_nvenc -preset p4 -tune ull -b:v 6000k -maxrate 6000k -bufsize 12000k -g 120 -c:a aac -b:a 160k -f flv "rtmp://a.rtmp.youtube.com/live2/je5p-8zxu-d7rj-d73s-cvu6"
pause
goto MENU

:STREAM_MULTI_RELAY
echo.
echo [*] Starting Broadcast to Local Relay Engine (Port 1935)...
echo [*] The relay duplicates stream to:
echo     - YouTube Live (rtmp://a.rtmp.youtube.com/live2/je5p-8zxu-d7rj-d73s-cvu6)
echo     - StehouwerPublishing.com Web Player (http://localhost/live)
echo.
ffmpeg -y -f gdigrab -framerate 60 -i desktop -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 -c:v h264_nvenc -preset p4 -tune ull -b:v 6000k -maxrate 6000k -bufsize 12000k -g 120 -c:a aac -b:a 160k -f flv "rtmp://127.0.0.1:1935/live/stehouwer"
pause
goto MENU

:STREAM_TEST_PATTERN
echo.
echo [*] Broadcasting 60-second 1080p60 Test Color Pattern + 1kHz Audio Tone...
ffmpeg -re -f lavfi -i "testsrc=size=1920x1080:rate=60" -f lavfi -i "sine=frequency=1000:sample_rate=48000" -c:v libx264 -preset ultrafast -tune zerolatency -b:v 4500k -c:a aac -b:a 128k -t 60 -f flv "rtmp://a.rtmp.youtube.com/live2/je5p-8zxu-d7rj-d73s-cvu6"
echo [*] Test pattern transmission completed.
pause
goto MENU

:LAUNCH_OBS
echo.
echo [*] Launching OBS Studio...
start "" "C:\Program Files\obs-studio\bin\64bit\obs64.exe"
if %ERRORLEVEL% neq 0 (
    start "" "C:\AI-BS\obs-core\bin\64bit\obs64.exe"
)
exit /b 0

:MENU
cls
goto :EOF
