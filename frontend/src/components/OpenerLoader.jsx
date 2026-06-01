import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

export default function OpenerLoader({ loading }) {
  const [progress, setProgress] = useState(0);
  const [webglSupported, setWebGLSupported] = useState(true);
  const [isVisible, setIsVisible] = useState(true);
  const canvasRef = useRef(null);

  // 1. Progress Bar Logic
  useEffect(() => {
    let interval;
    if (loading) {
      // Smoothly increment progress up to 90% while waiting for actual load
      interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) return prev;
          return prev + Math.floor(Math.random() * 5) + 1;
        });
      }, 100);
    } else {
      // Fast track to 100% when loading completes
      setProgress(100);
      const timeout = setTimeout(() => {
        setIsVisible(false);
      }, 800); // Allow fade out after a slight delay
      return () => clearTimeout(timeout);
    }
    return () => clearInterval(interval);
  }, [loading]);

  // 2. WebGL 3D Ball Renderer
  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");

    if (!gl) {
      setWebGLSupported(false);
      return;
    }

    setWebGLSupported(true);

    // Shaders
    const vsSource = `
      attribute vec3 aPosition;
      attribute vec3 aNormal;
      varying vec3 vNormal;
      varying vec3 vPosition;
      uniform mat4 uProjectionMatrix;
      uniform mat4 uViewMatrix;
      uniform mat4 uModelMatrix;
      void main() {
        vNormal = aNormal;
        vec4 pos = uModelMatrix * vec4(aPosition, 1.0);
        vPosition = pos.xyz;
        gl_Position = uProjectionMatrix * uViewMatrix * pos;
      }
    `;

    const fsSource = `
      precision mediump float;
      varying vec3 vNormal;
      varying vec3 vPosition;
      uniform mat3 uNormalMatrix;
      void main() {
        vec3 normal = normalize(uNormalMatrix * vNormal);
        vec3 lightDir = normalize(vec3(1.5, 2.0, 2.0));
        
        // Ambient (Deep Gold)
        vec3 ambient = vec3(0.25, 0.18, 0.02);
        
        // Diffuse (Championship Gold)
        float diff = max(dot(normal, lightDir), 0.0);
        vec3 diffuse = diff * vec3(0.85, 0.67, 0.18);
        
        // Specular (High shine gold highlights)
        vec3 viewDir = normalize(vec3(0.0, 0.0, 4.0) - vPosition);
        vec3 reflectDir = reflect(-lightDir, normal);
        float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
        vec3 specular = spec * vec3(1.0, 0.95, 0.7);
        
        // Add soccer pentagon wireframe grid overlay style via normal shading
        float grid = abs(sin(vPosition.x * 12.0) * sin(vPosition.y * 12.0) * sin(vPosition.z * 12.0));
        vec3 finalColor = ambient + diffuse + specular;
        if (grid < 0.1) {
          finalColor *= 0.7; // darken grid lines
        }
        
        gl_FragColor = vec4(finalColor, 1.0);
      }
    `;

    const loadShader = (type, source) => {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error("Shader compile error: " + gl.getShaderInfoLog(shader));
        gl.deleteShader(shader);
        return null;
      }
      return shader;
    };

    const vertexShader = loadShader(gl.VERTEX_SHADER, vsSource);
    const fragmentShader = loadShader(gl.FRAGMENT_SHADER, fsSource);
    const program = gl.createProgram();
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("Program link error");
      setWebGLSupported(false);
      return;
    }

    gl.useProgram(program);

    // Create Sphere Mesh (soccer ball shape)
    const vertices = [];
    const normals = [];
    const indices = [];
    const radius = 1.2;
    const segments = 24;

    for (let lat = 0; lat <= segments; lat++) {
      const theta = (lat * Math.PI) / segments;
      const sinTheta = Math.sin(theta);
      const cosTheta = Math.cos(theta);

      for (let lon = 0; lon <= segments; lon++) {
        const phi = (lon * 2 * Math.PI) / segments;
        const sinPhi = Math.sin(phi);
        const cosPhi = Math.cos(phi);

        const x = cosPhi * sinTheta;
        const y = cosTheta;
        const z = sinPhi * sinTheta;

        vertices.push(x * radius, y * radius, z * radius);
        normals.push(x, y, z);
      }
    }

    for (let lat = 0; lat < segments; lat++) {
      for (let lon = 0; lon < segments; lon++) {
        const first = lat * (segments + 1) + lon;
        const second = first + segments + 1;

        indices.push(first, second, first + 1);
        indices.push(second, second + 1, first + 1);
      }
    }

    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STATIC_DRAW);

    const normalBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, normalBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(normals), gl.STATIC_DRAW);

    const indexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(indices), gl.STATIC_DRAW);

    // Get attribute/uniform locations
    const aPosition = gl.getAttribLocation(program, "aPosition");
    const aNormal = gl.getAttribLocation(program, "aNormal");
    const uProjectionMatrix = gl.getUniformLocation(program, "uProjectionMatrix");
    const uViewMatrix = gl.getUniformLocation(program, "uViewMatrix");
    const uModelMatrix = gl.getUniformLocation(program, "uModelMatrix");
    const uNormalMatrix = gl.getUniformLocation(program, "uNormalMatrix");

    // Math utilities for Matrices
    const perspective = (fovy, aspect, near, far) => {
      const f = 1.0 / Math.tan(fovy / 2);
      const nf = 1.0 / (near - far);
      return [
        f / aspect, 0, 0, 0,
        0, f, 0, 0,
        0, 0, (far + near) * nf, -1,
        0, 0, 2 * far * near * nf, 0
      ];
    };

    const identity = () => [
      1, 0, 0, 0,
      0, 1, 0, 0,
      0, 0, 1, 0,
      0, 0, 0, 1
    ];

    const rotateY = (m, angle) => {
      const c = Math.cos(angle);
      const s = Math.sin(angle);
      const r = [...m];
      r[0] = m[0] * c - m[8] * s;
      r[2] = m[2] * c - m[10] * s;
      r[8] = m[0] * s + m[8] * c;
      r[10] = m[2] * s + m[10] * c;
      return r;
    };

    const rotateX = (m, angle) => {
      const c = Math.cos(angle);
      const s = Math.sin(angle);
      const r = [...m];
      r[4] = m[4] * c + m[8] * s;
      r[6] = m[6] * c + m[10] * s;
      r[8] = -m[4] * s + m[8] * c;
      r[10] = -m[6] * s + m[10] * c;
      return r;
    };

    const getNormalMatrix = (m) => {
      // Simplified: normal matrix is upper 3x3 of model matrix
      return [
        m[0], m[1], m[2],
        m[4], m[5], m[6],
        m[8], m[9], m[10]
      ];
    };

    // Render loop
    let angle = 0;
    let animationFrameId;

    const render = () => {
      gl.clearColor(0.0, 0.0, 0.0, 0.0);
      gl.clearDepth(1.0);
      gl.enable(gl.DEPTH_TEST);
      gl.depthFunc(gl.LEQUAL);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      // Matrices
      const aspect = canvas.width / canvas.height;
      const proj = perspective((45 * Math.PI) / 180, aspect, 0.1, 100.0);
      
      const view = identity();
      view[14] = -4.0; // translate Z

      let model = identity();
      model = rotateY(model, angle);
      model = rotateX(model, angle * 0.3);

      const normalMat = getNormalMatrix(model);

      // Bind attributes
      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
      gl.vertexAttribPointer(aPosition, 3, gl.FLOAT, false, 0, 0);
      gl.enableVertexAttribArray(aPosition);

      gl.bindBuffer(gl.ARRAY_BUFFER, normalBuffer);
      gl.vertexAttribPointer(aNormal, 3, gl.FLOAT, false, 0, 0);
      gl.enableVertexAttribArray(aNormal);

      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);

      // Set uniforms
      gl.uniformMatrix4fv(uProjectionMatrix, false, new Float32Array(proj));
      gl.uniformMatrix4fv(uViewMatrix, false, new Float32Array(view));
      gl.uniformMatrix4fv(uModelMatrix, false, new Float32Array(model));
      gl.uniformMatrix3fv(uNormalMatrix, false, new Float32Array(normalMat));

      gl.drawElements(gl.TRIANGLES, indices.length, gl.UNSIGNED_SHORT, 0);

      angle += 0.015;
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [webglSupported]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          key="opener-loader"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.05 }}
          transition={{ duration: 0.6, ease: "easeInOut" }}
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-gradient-to-br from-[hsl(332,85%,4%)] to-[hsl(231,64%,6%)] backdrop-blur-md"
        >
          {/* Glowing Aura Effect */}
          <div className="absolute top-1/2 left-1/2 w-96 h-96 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[hsl(46,68%,53%)] opacity-10 blur-[120px]" />

          {/* Ball Render Target */}
          <div className="relative w-64 h-64 flex items-center justify-center">
            {webglSupported ? (
              <canvas
                ref={canvasRef}
                width={300}
                height={300}
                className="w-full h-full"
              />
            ) : (
              // 2D Glowing Fallback
              <motion.svg
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 4, ease: "linear" }}
                className="w-48 h-48 drop-shadow-[0_0_25px_rgba(217,171,46,0.5)]"
                viewBox="0 0 100 100"
                fill="none"
              >
                <circle cx="50" cy="50" r="40" stroke="url(#goldGrad)" strokeWidth="3" strokeDasharray="12 6" />
                <path d="M50 15 L50 85 M15 50 L85 50" stroke="url(#goldGrad)" strokeWidth="1" />
                <defs>
                  <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#d9ab2e" />
                    <stop offset="100%" stopColor="#f4d160" />
                  </linearGradient>
                </defs>
              </motion.svg>
            )}

            {/* Core Shield Emblem Overlay */}
            <div className="absolute inset-0 flex items-center justify-center select-none pointer-events-none">
              <span className="text-[10px] tracking-[0.4em] font-bold text-white opacity-40 uppercase font-heading">
                FIFA 2026
              </span>
            </div>
          </div>

          {/* Loading Progress Information */}
          <div className="mt-8 flex flex-col items-center gap-4 w-72 z-10">
            <div className="flex justify-between items-end w-full text-white/70">
              <span className="text-xs tracking-[0.2em] font-heading font-semibold uppercase">Simulating Timeline</span>
              <span className="text-sm font-bold font-numeric text-[hsl(46,68%,53%)]">{progress}%</span>
            </div>
            
            {/* Liquid-Glass Progress track */}
            <div className="w-full h-[6px] bg-white/5 rounded-full overflow-hidden border border-white/5 p-[1px]">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.1 }}
                className="h-full bg-gradient-to-r from-[hsl(46,68%,53%)] to-[hsl(46,85%,58%)] rounded-full shadow-[0_0_10px_rgba(217,171,46,0.6)]"
              />
            </div>
            
            <p className="text-[10px] text-white/40 tracking-wider font-heading mt-2 animate-pulse">
              Crunching Elo metrics & historical vectors...
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
