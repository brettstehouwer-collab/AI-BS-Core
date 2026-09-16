class VSTProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    
    // We are maintaining a mono ring buffer for simplicity, matching the daemon's reshape(1, -1)
    // 44100 frames = 1 second of buffer capacity.
    this.bufferSize = 44100; 
    this.ringBuffer = new Float32Array(this.bufferSize);
    
    this.writeIndex = 0;
    this.readIndex = 0;
    
    // Lookahead margin: 512 frames (~11.6ms at 44.1kHz). 
    // This allows the python daemon to round-trip the payload before we try to read it.
    this.latencyMargin = 512;
    this.writeIndex = this.latencyMargin; // offset the writer ahead of the reader
    
    // Receive processed float32 arrays from the UI thread (WebSocket ingress)
    this.port.onmessage = (event) => {
      const incomingData = new Float32Array(event.data);
      for (let i = 0; i < incomingData.length; i++) {
        this.ringBuffer[this.writeIndex] = incomingData[i];
        this.writeIndex = (this.writeIndex + 1) % this.bufferSize;
      }
    };
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    
    if (!input || input.length === 0 || !input[0]) return true;

    // Send the dry input out to the UI thread (to be forwarded to WebSocket egress)
    // We clone the input channel 0 array so we don't transfer the underlying buffer that WebAudio is actively using.
    const drySignal = new Float32Array(input[0]);
    this.port.postMessage(drySignal.buffer, [drySignal.buffer]);

    // Read the delayed wet signal from the ring buffer and write to the output
    for (let channel = 0; channel < output.length; channel++) {
      const outChannel = output[channel];
      
      // We only have a mono ring buffer, so we write the same data to all output channels
      let tempReadIndex = this.readIndex; 
      
      for (let i = 0; i < outChannel.length; i++) {
        outChannel[i] = this.ringBuffer[tempReadIndex];
        // clear the buffer immediately after reading to prevent stale data looping
        this.ringBuffer[tempReadIndex] = 0.0; 
        tempReadIndex = (tempReadIndex + 1) % this.bufferSize;
      }
    }
    
    // Advance the primary read index by the chunk size (usually 128 frames)
    this.readIndex = (this.readIndex + output[0].length) % this.bufferSize;

    return true;
  }
}

registerProcessor('vst-processor', VSTProcessor);
