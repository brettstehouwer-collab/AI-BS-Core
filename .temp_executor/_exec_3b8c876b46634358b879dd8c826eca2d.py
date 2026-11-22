"""
Self-learning loop script for training an AI model across multiple domains ("areas"),
with a safety guard that periodically saves learned state, manages checkpoint files,
and enforces a disk usage limit to prevent uncontrolled file buildup.

This is a conceptual template. Replace dummy training steps with your actual AI training logic.
"""

import os
import time
import json
from pathlib import Path

# Configuration
TRAINING_AREAS = ['vision', 'language', 'audio', 'planning', 'motor_control']  # Example AI competency areas
MAX_DISK_USAGE_MB = 1000  # Max disk space for saved checkpoints/models
CHECKPOINT_DIR = Path('./ai_model_checkpoints')
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
SAVE_INTERVAL = 5  # Number of training iterations before saving
SLEEP_BETWEEN_ITERATIONS = 1  # Seconds between iterations (simulate time-consuming training)

def train_on_area(area, model_state):
    """
    Dummy training function for an AI area.
    Updates model_state with incremental progress.
    """
    print(f"Training AI on {area}...")
    # Simulate some training work here (replace with your logic)
    time.sleep(0.5)
    progress = model_state.get(area, 0)
    progress = min(progress + 5, 100)  # Increment progress by 5%, cap at 100%
    model_state[area] = progress
    print(f"Progress in {area}: {progress}%")
    return model_state

def save_model_state(state, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def load_latest_model_state():
    files = sorted(CHECKPOINT_DIR.glob('model_state_*.json'), reverse=True)
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                state = json.load(file)
                print(f"Loaded model state from {f}")
                return state
        except Exception as e:
            print(f"Warning: failed to load checkpoint {f}: {e}")
    return {}

def get_checkpoint_disk_usage_mb():
    total_bytes = sum(f.stat().st_size for f in CHECKPOINT_DIR.glob('model_state_*.json'))
    return total_bytes / (1024 * 1024)

def cleanup_old_checkpoints():
    files = sorted(CHECKPOINT_DIR.glob('model_state_*.json'), key=lambda f: f.stat().st_mtime)
    while get_checkpoint_disk_usage_mb() > MAX_DISK_USAGE_MB and files:
        oldest = files.pop(0)
        try:
            print(f"Deleting old checkpoint {oldest}")
            oldest.unlink()
        except Exception as e:
            print(f"Error deleting checkpoint {oldest}: {e}")

def main_training_loop():
    model_state = load_latest_model_state()
    iteration = 0

    while True:
        iteration += 1
        print(f"\n=== Training iteration {iteration} ===")

        for area in TRAINING_AREAS:
            model_state = train_on_area(area, model_state)

        if iteration % SAVE_INTERVAL == 0:
            timestamp = int(time.time())
            filename = CHECKPOINT_DIR / f"model_state_{timestamp}.json"
            save_model_state(model_state, filename)
            print(f"Saved model state checkpoint: {filename}")

            cleanup_old_checkpoints()
            usage = get_checkpoint_disk_usage_mb()
            print(f"Current disk usage for checkpoints: {usage:.2f} MB (limit: {MAX_DISK_USAGE_MB} MB)")

        # Check if training is complete across all areas
        if all(progress >= 100 for progress in model_state.values()):
            print("Training complete in all areas.")
            # Final save before exit
            final_file = CHECKPOINT_DIR / f"model_state_final_{int(time.time())}.json"
            save_model_state(model_state, final_file)
            print(f"Final model state saved: {final_file}")
            break

        time.sleep(SLEEP_BETWEEN_ITERATIONS)

if __name__ == '__main__':
    main_training_loop()