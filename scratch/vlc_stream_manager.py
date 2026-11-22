import subprocess
import os
import time

class VLCStreamManager:
    """
    Manages headless VLC instances to transcode and broadcast local video files as HLS streams.
    """
    def __init__(self, output_dir="C:\\AI-BS\\streams"):
        self.output_dir = output_dir
        self.vlc_path = r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
        self.current_process = None
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def start_stream(self, video_path: str):
        """
        Starts transcoding a video to HLS.
        """
        if self.current_process:
            self.stop_stream()

        # Clean old stream chunks
        for f in os.listdir(self.output_dir):
            if f.endswith('.ts') or f.endswith('.m3u8'):
                try:
                    os.remove(os.path.join(self.output_dir, f))
                except Exception:
                    pass

        m3u8_path = os.path.join(self.output_dir, "stream.m3u8")
        # Format the sout string for VLC HLS output
        # Transcode to h264/aac, mux to ts, output as livehttp to m3u8 playlist
        sout = (
            f"#transcode{{vcodec=h264,vb=800,scale=Auto,acodec=mp4a,ab=128,channels=2,samplerate=44100}}:"
            f"std{{access=livehttp,mux=ts,dst={self.output_dir}\\stream-%03d.ts,"
            f"index={m3u8_path},index-url=stream-%03d.ts}}"
        )

        cmd = [
            self.vlc_path,
            "-I", "dummy",       # Headless mode
            video_path,
            f"--sout={sout}",
            "--loop"             # Keep looping for testing
        ]

        print(f"🎬 Starting VLC HLS Stream for: {video_path}")
        self.current_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Give VLC a moment to generate the first few chunks
        time.sleep(2)
        return "stream.m3u8"

    def stop_stream(self):
        """
        Kills the running VLC instance.
        """
        if self.current_process:
            print("🛑 Stopping VLC HLS Stream...")
            self.current_process.kill()
            self.current_process = None

vlc_manager = VLCStreamManager()
