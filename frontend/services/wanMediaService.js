// frontend/services/wanMediaService.js

const BACKEND_URL = typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
  ? 'https://ai-bs-dashboard.web.app'
  : (import.meta.env.VITE_BACKEND_URL || 'http://localhost:8080');

const API_BASE = `${BACKEND_URL}/api/v1/wan-media`;

/**
 * Triggers Wan-Dancer-14B character motion choreography on Port 8189.
 * @param {string} prompt Motion / dance description
 * @param {string} characterImagePath Reference image path
 * @param {number} steps Sampling steps (default 30)
 * @param {number} frames Output length frames (default 81)
 */
export async function triggerWanDancer(prompt, characterImagePath = null, steps = 30, frames = 81) {
  const res = await fetch(`${API_BASE}/dance/animate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Client-ID": "stehouwer_publishing" },
    body: JSON.stringify({ prompt, character_image_path: characterImagePath, steps, frames })
  });
  return await res.json();
}

/**
 * Triggers WanSong text-to-soundtrack multi-track generation on Port 8189.
 * @param {string} moodPrompt Musical mood / instruments / prompt
 * @param {number} durationSeconds Duration in seconds (default 30)
 * @param {number} bpm Beats per minute (default 120)
 */
export async function triggerWanSong(moodPrompt, durationSeconds = 30, bpm = 120) {
  const res = await fetch(`${API_BASE}/audio/compose`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Client-ID": "stehouwer_publishing" },
    body: JSON.stringify({ mood_prompt: moodPrompt, duration_seconds: durationSeconds, bpm })
  });
  return await res.json();
}

/**
 * Polls media execution status from ComfyUI history.
 * @param {string} promptId ComfyUI prompt task ID
 */
export async function checkWanMediaStatus(promptId) {
  const res = await fetch(`${API_BASE}/status/${promptId}`, {
    headers: { "X-Client-ID": "stehouwer_publishing" }
  });
  return await res.json();
}
