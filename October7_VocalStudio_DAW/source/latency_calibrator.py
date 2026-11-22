import numpy as np
import sounddevice as sd
from scipy.signal import chirp, fftconvolve
import soundfile as sf
from typing import Tuple, Optional


class LoopbackCalibrator:
    def __init__(
        self,
        sample_rate: int = 48000,
        chirp_duration: float = 0.5,
        pad_duration: float = 0.3,
        f0: float = 100.0,
        f1: float = 10000.0
    ):
        self.sample_rate = sample_rate
        self.chirp_duration = chirp_duration
        self.pad_duration = pad_duration
        self.f0 = f0
        self.f1 = f1
        self.probe_signal, self.pad_samples = self._generate_probe()

    def _generate_probe(self) -> Tuple[np.ndarray, int]:
        """Generates a logarithmic sine chirp bracketed by leading and trailing silence."""
        pad_samples = int(self.pad_duration * self.sample_rate)
        chirp_samples = int(self.chirp_duration * self.sample_rate)
        t = np.linspace(0, self.chirp_duration, chirp_samples, endpoint=False)
        
        # Logarithmic chirp with Hann taper to avoid boundary clicks
        raw_chirp = chirp(t, f0=self.f0, t1=self.chirp_duration, f1=self.f1, method='logarithmic')
        envelope = np.hanning(chirp_samples)
        tapered_chirp = (raw_chirp * envelope * 0.7).astype(np.float32)

        # Full probe: [Pre-Pad (silence)] + [Chirp] + [Post-Pad (silence)]
        probe = np.concatenate([
            np.zeros(pad_samples, dtype=np.float32),
            tapered_chirp,
            np.zeros(pad_samples * 2, dtype=np.float32)
        ])
        return probe, pad_samples

    def run_calibration(
        self,
        input_device: Optional[int] = None,
        output_device: Optional[int] = None,
        snr_threshold_db: float = 15.0
    ) -> dict:
        """
        Executes duplex playback and capture, computing sample latency.
        Requires loopback (headphone bleed / cable / speaker loop) connecting output to input.
        """
        probe_out = self.probe_signal.reshape(-1, 1)

        # WASAPI Exclusive mode flag configuration via sounddevice
        wasapi_exclusive = sd.WasapiSettings(exclusive=True)

        try:
            recorded = sd.playrec(
                probe_out,
                samplerate=self.sample_rate,
                channels=1,
                device=(input_device, output_device),
                dtype='float32',
                extra_settings=(wasapi_exclusive, wasapi_exclusive)
            )
            sd.wait()
        except Exception:
            # Fallback to shared WASAPI if exclusive access is blocked
            recorded = sd.playrec(
                probe_out,
                samplerate=self.sample_rate,
                channels=1,
                device=(input_device, output_device),
                dtype='float32'
            )
            sd.wait()

        recorded_mono = recorded.flatten()
        reference = self.probe_signal[self.pad_samples: self.pad_samples + int(self.chirp_duration * self.sample_rate)]

        # FFT Cross-Correlation: reference time-reversed convolution
        correlation = fftconvolve(recorded_mono, reference[::-1], mode='full')
        peak_idx = int(np.argmax(np.abs(correlation)))

        # Latency calculation relative to when chirp began
        matched_start = peak_idx - len(reference) + 1
        latency_samples = matched_start - self.pad_samples

        # Signal-to-Noise Ratio (Peak to Noise Floor) validation
        peak_amp = np.abs(correlation[peak_idx])
        noise_floor = np.median(np.abs(correlation)) + 1e-12
        snr_db = 20 * np.log10(peak_amp / noise_floor)

        if latency_samples < 0:
            latency_samples = 0

        latency_ms = (latency_samples / self.sample_rate) * 1000.0

        return {
            "latency_samples": int(latency_samples),
            "latency_ms": round(float(latency_ms), 2),
            "snr_db": round(float(snr_db), 2),
            "sample_rate": self.sample_rate
        }

    @staticmethod
    def align_take(audio_data: np.ndarray, latency_samples: int) -> np.ndarray:
        """Shifts audio back by latency_samples, padding tail with silence."""
        if latency_samples <= 0:
            return audio_data
        
        if audio_data.ndim == 1:
            shifted = audio_data[latency_samples:]
            return np.pad(shifted, (0, latency_samples), mode='constant')
        else:
            shifted = audio_data[:, latency_samples:]
            return np.pad(shifted, ((0, 0), (0, latency_samples)), mode='constant')
