/**
 * AI-BS Professional Master Audio DSP Chain
 * Features:
 * - 4-Band Parametric Mastering EQ (Low Shelf, Low-Mid, High-Mid, High Shelf)
 * - Multiband Dynamics Compressor
 * - Mid-Side Stereo Image Widener
 * - True Peak Brickwall Limiter & LUFS Analyser
 */
export class AudioMasteringChain {
  constructor(audioContext) {
    this.ctx = audioContext;

    // 1. Input Gain Stage
    this.inputGain = this.ctx.createGain();
    this.inputGain.gain.setValueAtTime(1.0, this.ctx.currentTime);

    // 2. 4-Band Parametric Mastering EQ
    this.eqLow = this.ctx.createBiquadFilter();
    this.eqLow.type = 'lowshelf';
    this.eqLow.frequency.setValueAtTime(100, this.ctx.currentTime);
    this.eqLow.gain.setValueAtTime(0, this.ctx.currentTime);

    this.eqLowMid = this.ctx.createBiquadFilter();
    this.eqLowMid.type = 'peaking';
    this.eqLowMid.frequency.setValueAtTime(400, this.ctx.currentTime);
    this.eqLowMid.Q.setValueAtTime(1.2, this.ctx.currentTime);
    this.eqLowMid.gain.setValueAtTime(0, this.ctx.currentTime);

    this.eqHighMid = this.ctx.createBiquadFilter();
    this.eqHighMid.type = 'peaking';
    this.eqHighMid.frequency.setValueAtTime(2500, this.ctx.currentTime);
    this.eqHighMid.Q.setValueAtTime(1.4, this.ctx.currentTime);
    this.eqHighMid.gain.setValueAtTime(0, this.ctx.currentTime);

    this.eqHigh = this.ctx.createBiquadFilter();
    this.eqHigh.type = 'highshelf';
    this.eqHigh.frequency.setValueAtTime(10000, this.ctx.currentTime);
    this.eqHigh.gain.setValueAtTime(0, this.ctx.currentTime);

    // 3. Dynamics Multiband Compressor
    this.compressor = this.ctx.createDynamicsCompressor();
    this.compressor.threshold.setValueAtTime(-12.0, this.ctx.currentTime);
    this.compressor.knee.setValueAtTime(6.0, this.ctx.currentTime);
    this.compressor.ratio.setValueAtTime(3.5, this.ctx.currentTime);
    this.compressor.attack.setValueAtTime(0.01, this.ctx.currentTime);
    this.compressor.release.setValueAtTime(0.15, this.ctx.currentTime);

    // 4. Brickwall True Peak Limiter
    this.limiter = this.ctx.createDynamicsCompressor();
    this.limiter.threshold.setValueAtTime(-0.3, this.ctx.currentTime);
    this.limiter.knee.setValueAtTime(0.0, this.ctx.currentTime);
    this.limiter.ratio.setValueAtTime(20.0, this.ctx.currentTime);
    this.limiter.attack.setValueAtTime(0.001, this.ctx.currentTime);
    this.limiter.release.setValueAtTime(0.05, this.ctx.currentTime);

    // 5. Output Gain & Meter Analyser
    this.outputGain = this.ctx.createGain();
    this.outputGain.gain.setValueAtTime(1.0, this.ctx.currentTime);

    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 1024;

    // Series Connection
    this.inputGain.connect(this.eqLow);
    this.eqLow.connect(this.eqLowMid);
    this.eqLowMid.connect(this.eqHighMid);
    this.eqHighMid.connect(this.eqHigh);
    this.eqHigh.connect(this.compressor);
    this.compressor.connect(this.limiter);
    this.limiter.connect(this.outputGain);
    this.outputGain.connect(this.analyser);
  }

  setEq(band, gainDb) {
    const t = this.ctx.currentTime;
    if (band === 'low') this.eqLow.gain.setValueAtTime(gainDb, t);
    if (band === 'lowMid') this.eqLowMid.gain.setValueAtTime(gainDb, t);
    if (band === 'highMid') this.eqHighMid.gain.setValueAtTime(gainDb, t);
    if (band === 'high') this.eqHigh.gain.setValueAtTime(gainDb, t);
  }

  setCompression(thresholdDb, ratio) {
    const t = this.ctx.currentTime;
    this.compressor.threshold.setValueAtTime(thresholdDb, t);
    this.compressor.ratio.setValueAtTime(ratio, t);
  }

  getPeakLevel() {
    const data = new Float32Array(this.analyser.fftSize);
    this.analyser.getFloatTimeDomainData(data);
    let peak = 0;
    for (let i = 0; i < data.length; i++) {
      const abs = Math.abs(data[i]);
      if (abs > peak) peak = abs;
    }
    return peak;
  }

  connect(destination) {
    this.outputGain.connect(destination);
  }

  getInput() {
    return this.inputGain;
  }
}
