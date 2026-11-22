export class WebGLCompositor {
  constructor(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext('webgl2', { premultipliedAlpha: false, preserveDrawingBuffer: true });
    if (!this.gl) {
      console.warn('WebGL2 not supported, falling back to 2D canvas');
    }
  }

  renderFrame(sources) {
    if (!this.gl) return;
    const gl = this.gl;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0.03, 0.05, 0.09, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);
  }
}
