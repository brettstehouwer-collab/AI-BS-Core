import numpy as np
import librosa
from scipy.ndimage import median_filter
import mido
from mido import Message, MidiFile, MidiTrack, MetaMessage
from dataclasses import dataclass
from typing import List


@dataclass
class DetectedNote:
    start_time: float
    end_time: float
    midi_pitch: int
    velocity: int
    name: str = ""
    cents: int = 0


class VocalToMidiConverter:
    NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def __init__(
        self,
        sample_rate: int = 44100,
        hop_length: int = 512,
        fmin: float = 65.41,   # C2
        fmax: float = 1046.50, # C6
        energy_threshold_db: float = -38.0,
        min_note_duration: float = 0.08  # 80ms minimum note length
    ):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.fmin = fmin
        self.fmax = fmax
        self.energy_threshold_db = energy_threshold_db
        self.min_note_duration = min_note_duration

    def get_note_name(self, midi_pitch: int) -> str:
        octave = (midi_pitch // 12) - 1
        name = self.NOTE_NAMES[midi_pitch % 12]
        return f"{name}{octave}"

    def process(self, audio: np.ndarray, tempo_bpm: float = 80.0) -> List[DetectedNote]:
        """Extracts pitch tracks, groups stable pitches into discrete notes, and computes MIDI attributes."""
        if audio.ndim > 1:
            audio = librosa.to_mono(audio)

        # 1. Energy Analysis (RMS)
        rms = librosa.feature.rms(y=audio, hop_length=self.hop_length)[0]
        db = librosa.amplitude_to_db(rms, ref=np.max)

        # 2. Fundamental Frequency Estimation via pYIN
        f0, voiced_flag, voiced_prob = librosa.pyin(
            audio,
            fmin=self.fmin,
            fmax=self.fmax,
            sr=self.sample_rate,
            hop_length=self.hop_length,
            fill_na=0.0
        )

        # 3. Energy Gate & Frequency to Continuous MIDI Pitch
        valid_mask = (voiced_flag) & (voiced_prob > 0.45) & (db > self.energy_threshold_db)
        
        midi_pitches = np.zeros_like(f0)
        valid_indices = np.where(valid_mask & (f0 > 0))[0]
        midi_pitches[valid_indices] = 69.0 + 12.0 * np.log2(f0[valid_indices] / 440.0)

        # 4. Vibrato Smoothing via Median Filter (window = 5 frames ~ 58ms)
        smoothed_pitches = median_filter(midi_pitches, size=5)

        # 5. Note Clustering and Segmentation
        frame_time = self.hop_length / self.sample_rate
        notes: List[DetectedNote] = []
        
        current_pitch = None
        start_frame = 0
        collected_energies = []
        collected_cents = []

        for idx, (is_valid, pitch) in enumerate(zip(valid_mask, smoothed_pitches)):
            rounded_pitch = int(np.round(pitch)) if is_valid else None
            cents_dev = int(np.round((pitch - rounded_pitch) * 100)) if (is_valid and rounded_pitch is not None) else 0

            if rounded_pitch == current_pitch:
                if is_valid:
                    collected_energies.append(rms[idx])
                    collected_cents.append(cents_dev)
                continue

            # End current note if active
            if current_pitch is not None:
                duration = (idx - start_frame) * frame_time
                if duration >= self.min_note_duration:
                    avg_energy = float(np.mean(collected_energies)) if collected_energies else 0.01
                    velocity = int(np.clip((avg_energy / (np.max(rms) + 1e-6)) * 127, 40, 127))
                    avg_cents = int(np.mean(collected_cents)) if collected_cents else 0
                    
                    notes.append(DetectedNote(
                        start_time=round(start_frame * frame_time, 3),
                        end_time=round(idx * frame_time, 3),
                        midi_pitch=current_pitch,
                        velocity=velocity,
                        name=self.get_note_name(current_pitch),
                        cents=avg_cents
                    ))

            # Begin new note cluster
            current_pitch = rounded_pitch
            start_frame = idx
            collected_energies = [rms[idx]] if is_valid else []
            collected_cents = [cents_dev] if is_valid else []

        # Flush final note boundary
        if current_pitch is not None:
            duration = (len(smoothed_pitches) - start_frame) * frame_time
            if duration >= self.min_note_duration:
                avg_energy = float(np.mean(collected_energies)) if collected_energies else 0.01
                velocity = int(np.clip((avg_energy / (np.max(rms) + 1e-6)) * 127, 40, 127))
                avg_cents = int(np.mean(collected_cents)) if collected_cents else 0
                notes.append(DetectedNote(
                    start_time=round(start_frame * frame_time, 3),
                    end_time=round(len(smoothed_pitches) * frame_time, 3),
                    midi_pitch=current_pitch,
                    velocity=velocity,
                    name=self.get_note_name(current_pitch),
                    cents=avg_cents
                ))

        return notes

    def export_midi(self, notes: List[DetectedNote], output_path: str, tempo_bpm: float = 80.0):
        """Encodes detected notes into a Type 0 Standard MIDI File with delta tick timestamps."""
        mid = MidiFile(type=0, ticks_per_beat=480)
        track = MidiTrack()
        mid.tracks.append(track)

        # Set Tempo
        tempo_us = mido.bpm2tempo(tempo_bpm)
        track.append(MetaMessage('set_tempo', tempo=tempo_us, time=0))

        # Flatten Note On and Note Off timeline events
        events = []
        for note in notes:
            events.append((note.start_time, 'note_on', note.midi_pitch, note.velocity))
            events.append((note.end_time, 'note_off', note.midi_pitch, 0))

        # Sort chronologically, prioritizing Note Off at boundary collisions
        events.sort(key=lambda x: (x[0], 0 if x[1] == 'note_off' else 1))

        # Translate seconds to MIDI ticks
        ticks_per_second = (480 * (tempo_bpm / 60.0))
        last_tick = 0

        for timestamp, event_type, pitch, velocity in events:
            current_tick = int(np.round(timestamp * ticks_per_second))
            delta_ticks = max(0, current_tick - last_tick)
            
            track.append(Message(
                event_type,
                note=pitch,
                velocity=velocity,
                time=delta_ticks
            ))
            last_tick = current_tick

        track.append(MetaMessage('end_of_track', time=0))
        mid.save(output_path)
