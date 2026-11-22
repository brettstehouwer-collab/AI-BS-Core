export class AudioMasteringChain {
  constructor() {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    // Create Master Dynamics Compressor (Limiter)
    this.masterLimiter = this.audioContext.createDynamicsCompressor();
    this.masterLimiter.threshold.value = -3.0; // Hard limit at -3dB
    this.masterLimiter.knee.value = 0.0;
    this.masterLimiter.ratio.value = 20.0;
    this.masterLimiter.attack.value = 0.005;
    this.masterLimiter.release.value = 0.050;

    // Create Master EQ (Biquad Filter - High Shelf to add slight air)
    this.masterEQ = this.audioContext.createBiquadFilter();
    this.masterEQ.type = 'highshelf';
    this.masterEQ.frequency.value = 10000;
    this.masterEQ.gain.value = 2.0; // +2dB at 10kHz

    // Route chain
    this.masterEQ.connect(this.masterLimiter);
    this.masterLimiter.connect(this.audioContext.destination);
    
    this.channels = new Map();
  }

  addChannel(id, mediaStream) {
    if (!mediaStream || mediaStream.getAudioTracks().length === 0) return;
    
    const sourceNode = this.audioContext.createMediaStreamSource(mediaStream);
    const gainNode = this.audioContext.createGain();
    
    // Default gain to 1.0 (100%)
    gainNode.gain.value = 1.0;
    
    sourceNode.connect(gainNode);
    gainNode.connect(this.masterEQ);
    
    // Analyser node for VU meters
    const analyserNode = this.audioContext.createAnalyser();
    analyserNode.fftSize = 256;
    gainNode.connect(analyserNode);

    this.channels.set(id, {
      source: sourceNode,
      gain: gainNode,
      analyser: analyserNode,
      muted: false,
      previousGain: 1.0
    });
  }

  removeChannel(id) {
    if (this.channels.has(id)) {
      const channel = this.channels.get(id);
      channel.source.disconnect();
      channel.gain.disconnect();
      channel.analyser.disconnect();
      this.channels.delete(id);
    }
  }

  setVolume(id, volume) {
    if (this.channels.has(id)) {
      const channel = this.channels.get(id);
      // Volume is 0-100, normalize to 0.0-1.0
      const normalizedVolume = Math.max(0, Math.min(100, volume)) / 100;
      if (!channel.muted) {
        channel.gain.gain.setTargetAtTime(normalizedVolume, this.audioContext.currentTime, 0.05);
      }
      channel.previousGain = normalizedVolume;
    }
  }

  setMute(id, mute) {
    if (this.channels.has(id)) {
      const channel = this.channels.get(id);
      channel.muted = mute;
      const targetGain = mute ? 0.0 : channel.previousGain;
      channel.gain.gain.setTargetAtTime(targetGain, this.audioContext.currentTime, 0.05);
    }
  }

  getPeak(id) {
    if (this.channels.has(id)) {
      const channel = this.channels.get(id);
      const dataArray = new Uint8Array(channel.analyser.frequencyBinCount);
      channel.analyser.getByteTimeDomainData(dataArray);
      
      let maxAmplitude = 0;
      for (let i = 0; i < dataArray.length; i++) {
        // Values center around 128
        const amplitude = Math.abs(dataArray[i] - 128);
        if (amplitude > maxAmplitude) {
          maxAmplitude = amplitude;
        }
      }
      // Return peak as 0-100%
      return Math.min(100, (maxAmplitude / 128) * 100);
    }
    return 0;
  }

  resume() {
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
  }
}
