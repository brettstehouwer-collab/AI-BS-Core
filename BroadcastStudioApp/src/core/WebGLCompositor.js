export class WebGLCompositor {
  constructor(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext('webgl2', { premultipliedAlpha: false, preserveDrawingBuffer: true });
    
    if (!this.gl) {
      console.error('WebGL2 is not supported.');
      return;
    }
    
    this.initShaders();
    this.initBuffers();
  }

  initShaders() {
    const gl = this.gl;
    
    const vsSource = `#version 300 es
      in vec2 a_position;
      in vec2 a_texCoord;
      out vec2 v_texCoord;
      void main() {
        gl_Position = vec4(a_position, 0.0, 1.0);
        v_texCoord = a_texCoord;
      }
    `;

    // Basic Chroma Key (Green Screen) shader
    const fsSource = `#version 300 es
      precision mediump float;
      in vec2 v_texCoord;
      uniform sampler2D u_image;
      uniform vec3 u_keyColor;
      uniform float u_similarity;
      uniform float u_smoothness;
      out vec4 outColor;
      
      void main() {
        vec4 texColor = texture(u_image, v_texCoord);
        
        // Simple chroma key math
        float chromaDist = distance(texColor.rgb, u_keyColor);
        float alpha = smoothstep(u_similarity, u_similarity + u_smoothness, chromaDist);
        
        outColor = vec4(texColor.rgb, texColor.a * alpha);
      }
    `;

    this.program = this.createProgram(vsSource, fsSource);
    
    this.positionAttributeLocation = gl.getAttribLocation(this.program, "a_position");
    this.texCoordAttributeLocation = gl.getAttribLocation(this.program, "a_texCoord");
    
    this.imageLocation = gl.getUniformLocation(this.program, "u_image");
    this.keyColorLocation = gl.getUniformLocation(this.program, "u_keyColor");
    this.similarityLocation = gl.getUniformLocation(this.program, "u_similarity");
    this.smoothnessLocation = gl.getUniformLocation(this.program, "u_smoothness");
  }

  createShader(type, source) {
    const gl = this.gl;
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.error(gl.getShaderInfoLog(shader));
      gl.deleteShader(shader);
      return null;
    }
    return shader;
  }

  createProgram(vsSource, fsSource) {
    const gl = this.gl;
    const vertexShader = this.createShader(gl.VERTEX_SHADER, vsSource);
    const fragmentShader = this.createShader(gl.FRAGMENT_SHADER, fsSource);
    
    const program = gl.createProgram();
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error(gl.getProgramInfoLog(program));
      return null;
    }
    return program;
  }

  initBuffers() {
    const gl = this.gl;
    this.vao = gl.createVertexArray();
    gl.bindVertexArray(this.vao);

    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1.0, -1.0,
       1.0, -1.0,
      -1.0,  1.0,
      -1.0,  1.0,
       1.0, -1.0,
       1.0,  1.0,
    ]), gl.STATIC_DRAW);
    
    gl.enableVertexAttribArray(this.positionAttributeLocation);
    gl.vertexAttribPointer(this.positionAttributeLocation, 2, gl.FLOAT, false, 0, 0);

    const texCoordBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, texCoordBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      0.0, 1.0,
      1.0, 1.0,
      0.0, 0.0,
      0.0, 0.0,
      1.0, 1.0,
      1.0, 0.0,
    ]), gl.STATIC_DRAW);
    
    gl.enableVertexAttribArray(this.texCoordAttributeLocation);
    gl.vertexAttribPointer(this.texCoordAttributeLocation, 2, gl.FLOAT, false, 0, 0);
  }

  createTexture() {
    const gl = this.gl;
    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    return texture;
  }

  updateTexture(texture, videoElement) {
    if (!videoElement || videoElement.readyState < 2) return;
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, videoElement);
  }

  renderFrame(sources) {
    if (!this.gl || !this.program) return;
    const gl = this.gl;

    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0.05, 0.05, 0.05, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    gl.useProgram(this.program);
    gl.bindVertexArray(this.vao);

    // Enable blending for transparency
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    for (const source of sources) {
      if (!source.enabled || !source.active || !source.videoElement) continue;
      
      if (!source.texture) {
        source.texture = this.createTexture();
      }
      this.updateTexture(source.texture, source.videoElement);

      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, source.texture);
      gl.uniform1i(this.imageLocation, 0);

      // Simple chromakey uniforms (can be made configurable per source)
      gl.uniform3f(this.keyColorLocation, 0.0, 1.0, 0.0); // Pure green
      gl.uniform1f(this.similarityLocation, source.chromaSimilarity || 0.4);
      gl.uniform1f(this.smoothnessLocation, source.chromaSmoothness || 0.1);

      gl.drawArrays(gl.TRIANGLES, 0, 6);
    }
  }
}
