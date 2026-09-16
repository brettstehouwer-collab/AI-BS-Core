import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def extract_last_frame(video_path: str, output_image_path: str) -> bool:
    """Extracts the very last frame of a video using ffmpeg and saves it as a PNG."""
    if not os.path.exists(video_path):
        logger.error(f"Cannot extract frame. Video does not exist: {video_path}")
        return False

    try:
        # Seek to the end, extract exactly 1 frame.
        # We use -sseof -1 to start searching 1 second before the end, then vframes 1
        cmd = [
            "ffmpeg",
            "-y",                   # Overwrite output
            "-sseof", "-1",         # Start 1 second before EOF
            "-i", video_path,
            "-update", "1",
            "-q:v", "2",
            "-vframes", "1",        # Grab 1 frame
            output_image_path
        ]
        
        logger.info(f"Extracting last frame from {video_path}...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFMPEG frame extraction failed: {result.stderr}")
            return False
            
        logger.info(f"Successfully extracted last frame to {output_image_path}")
        return True
    except Exception as e:
        logger.error(f"Exception during frame extraction: {e}")
        return False

def stitch_videos_ffmpeg(video_paths: list, output_video_path: str) -> bool:
    """Stitches a list of MP4 videos sequentially using ffmpeg concat."""
    if not video_paths:
        return False

    # Create a temporary concat file
    concat_list_path = os.path.join(os.path.dirname(output_video_path), "ffmpeg_concat_list.txt")
    
    try:
        with open(concat_list_path, "w") as f:
            for vp in video_paths:
                # FFMPEG requires forward slashes or escaped backslashes in concat files
                safe_vp = vp.replace('\\', '/')
                f.write(f"file '{safe_vp}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            output_video_path
        ]
        
        logger.info(f"Stitching {len(video_paths)} videos to {output_video_path}...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFMPEG stitching failed: {result.stderr}")
            return False
            
        logger.info(f"Successfully stitched final video: {output_video_path}")
        return True
    except Exception as e:
        logger.error(f"Exception during video stitching: {e}")
        return False
    finally:
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)
