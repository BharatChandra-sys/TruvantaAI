'use client';

// "Convergence": many sources drift in, weak ones are pushed away, the rest
// stack into one verdict card. One instanced draw call plus one card.

import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { PerformanceMonitor } from '@react-three/drei';
import type { MotionValue } from 'motion/react';

const COUNT = 120;
const CARD_W = 1;
const CARD_H = 0.62;
const STACK_SCALE = 3.4;
const START_SCALE = 0.7;

const cardVertex = /* glsl */ `
  attribute float aTone;
  varying vec2 vUv;
  varying float vTone;
  void main() {
    vUv = uv;
    vTone = aTone;
    gl_Position = projectionMatrix * viewMatrix * modelMatrix * instanceMatrix * vec4(position, 1.0);
  }
`;

const cardFragment = /* glsl */ `
  uniform vec2 uSize;
  varying vec2 vUv;
  varying float vTone;

  float sdRoundRect(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
  }

  float bar(vec2 p, float y, float w) {
    vec2 q = p - vec2(-uSize.x * 0.5 + 0.1 + w * 0.5, y);
    return 1.0 - step(0.0, sdRoundRect(q, vec2(w * 0.5, 0.018), 0.018));
  }

  void main() {
    vec2 p = (vUv - 0.5) * uSize;
    float d = sdRoundRect(p, uSize * 0.5, 0.07);
    float aa = fwidth(d);
    float shape = 1.0 - smoothstep(-aa, aa, d);
    float edge = smoothstep(-0.02 - aa, -0.02 + aa, d) * shape;
    float lines = max(max(bar(p, 0.13, 0.42), bar(p, 0.0, 0.62)), bar(p, -0.13, 0.5)) * (1.0 - edge);

    vec3 fill = vec3(0.085, 0.085, 0.095);
    vec3 col = mix(fill, vec3(0.93), edge * vTone + lines * vTone * 0.35);
    float alpha = shape * (0.55 + 0.45 * edge) * clamp(vTone * 1.6, 0.0, 1.0);
    if (alpha < 0.01) discard;
    gl_FragColor = vec4(col, alpha);
  }
`;

type Seeds = {
  start: THREE.Vector3[];
  end: THREE.Vector3[];
  startRot: THREE.Quaternion[];
  endRot: THREE.Quaternion[];
  endScale: number[];
  rejected: boolean[];
  delay: number[];
  tone: number[];
};

function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function makeSeeds(): Seeds {
  const rand = mulberry32(7);
  const s: Seeds = { start: [], end: [], startRot: [], endRot: [], endScale: [], rejected: [], delay: [], tone: [] };
  const euler = new THREE.Euler();
  let stacked = 0;
  for (let i = 0; i < COUNT; i++) {
    const dir = new THREE.Vector3(rand() * 2 - 1, rand() * 2 - 1, rand() * 2 - 1).normalize();
    const r = 3.6 + rand() * 3.2;
    s.start.push(new THREE.Vector3(dir.x * r * 1.7, dir.y * r * 0.85, dir.z * r * 0.6 - 1));
    s.startRot.push(new THREE.Quaternion().setFromEuler(euler.set((rand() - 0.5) * 1.2, (rand() - 0.5) * 1.4, (rand() - 0.5) * 0.8)));

    const rejected = i % 4 === 0;
    s.rejected.push(rejected);
    if (rejected) {
      const rr = 8 + rand() * 3;
      s.end.push(new THREE.Vector3(dir.x * rr * 1.4, dir.y * rr * 0.7, -2 - rand() * 3));
      s.endRot.push(new THREE.Quaternion().setFromEuler(euler.set((rand() - 0.5) * 1.6, (rand() - 0.5) * 1.6, (rand() - 0.5))));
      s.endScale.push(0.8);
    } else {
      s.end.push(new THREE.Vector3((rand() - 0.5) * 0.2, (rand() - 0.5) * 0.14, -0.12 - stacked * 0.01));
      s.endRot.push(new THREE.Quaternion().setFromEuler(euler.set(0, 0, (rand() - 0.5) * 0.05)));
      s.endScale.push(STACK_SCALE);
      stacked++;
    }
    s.delay.push(rand() * 0.35);
    s.tone.push(0.18 + rand() * 0.3);
  }
  return s;
}

// Scratch objects reused every frame.
const dummy = new THREE.Object3D();
const q = new THREE.Quaternion();

const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

function verdictTexture() {
  const W = 1024;
  const H = Math.round(W * (CARD_H / CARD_W));
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const g = c.getContext('2d')!;
  const font = getComputedStyle(document.body).fontFamily;
  const rr = (x: number, y: number, w: number, h: number, r: number) => {
    g.beginPath();
    g.roundRect(x, y, w, h, r);
  };

  rr(3, 3, W - 6, H - 6, 44);
  g.fillStyle = '#17171a';
  g.fill();
  g.lineWidth = 4;
  g.strokeStyle = '#ffc53d';
  g.stroke();

  rr(64, 64, 168, 56, 28);
  g.fillStyle = 'rgba(61,214,140,0.14)';
  g.fill();
  g.fillStyle = '#3dd68c';
  g.beginPath();
  g.arc(96, 92, 7, 0, Math.PI * 2);
  g.fill();
  g.font = `500 30px ${font}`;
  g.textBaseline = 'middle';
  g.fillText('True', 116, 93);

  g.fillStyle = '#a1a1aa';
  g.font = `400 26px ui-monospace, monospace`;
  g.textAlign = 'right';
  g.fillText('97% confidence', W - 64, 93);
  g.textAlign = 'left';

  rr(64, 150, W - 128, 6, 3);
  g.fillStyle = '#1f1f23';
  g.fill();
  rr(64, 150, (W - 128) * 0.97, 6, 3);
  g.fillStyle = '#3dd68c';
  g.fill();

  g.fillStyle = '#2a2a2f';
  [0.86, 0.72].forEach((w, i) => {
    rr(64, 200 + i * 38, (W - 128) * w, 16, 8);
    g.fill();
  });
  g.fillStyle = '#111113';
  [0, 1].forEach((i) => {
    rr(64, 300 + i * 150, W - 128, 120, 20);
    g.fill();
  });
  g.fillStyle = '#2a2a2f';
  [0, 1].forEach((i) => {
    rr(96, 340 + i * 150, 40, 40, 10);
    g.fill();
    rr(160, 352 + i * 150, 360 - i * 60, 16, 8);
    g.fill();
  });

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

function Convergence({ progress }: { progress: MotionValue<number> }) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const verdict = useRef<THREE.Mesh>(null);
  const group = useRef<THREE.Group>(null);
  const seeds = useMemo(() => makeSeeds(), []);
  const texture = useMemo(() => verdictTexture(), []);
  const toneAttr = useMemo(() => new THREE.InstancedBufferAttribute(new Float32Array(COUNT), 1), []);
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: cardVertex,
        fragmentShader: cardFragment,
        uniforms: { uSize: { value: new THREE.Vector2(CARD_W, CARD_H) } },
        transparent: true,
        depthWrite: false,
      }),
    [],
  );
  const geometry = useMemo(() => {
    const g = new THREE.PlaneGeometry(CARD_W, CARD_H);
    g.setAttribute('aTone', toneAttr);
    return g;
  }, [toneAttr]);

  useEffect(
    () => () => {
      material.dispose();
      geometry.dispose();
      texture.dispose();
    },
    [material, geometry, texture],
  );

  useFrame((state) => {
    if (!mesh.current || !group.current || !verdict.current) return;
    const tones = mesh.current.geometry.getAttribute('aTone') as THREE.InstancedBufferAttribute;
    const p = smooth(0.08, 0.62, progress.get());
    const t = state.clock.elapsedTime;

    for (let i = 0; i < COUNT; i++) {
      const k = smooth(seeds.delay[i], seeds.delay[i] + 0.6, p);
      dummy.position.lerpVectors(seeds.start[i], seeds.end[i], k);
      q.copy(seeds.startRot[i]).slerp(seeds.endRot[i], k);
      dummy.quaternion.copy(q);
      dummy.scale.setScalar(START_SCALE + (seeds.endScale[i] - START_SCALE) * k);
      dummy.updateMatrix();
      mesh.current.setMatrixAt(i, dummy.matrix);
      const endTone = seeds.rejected[i] ? 0.14 : 0.3;
      tones.setX(i, seeds.tone[i] + (endTone - seeds.tone[i]) * k);
    }
    mesh.current.instanceMatrix.needsUpdate = true;
    tones.needsUpdate = true;

    const v = smooth(0.62, 0.95, p);
    const vm = verdict.current.material as THREE.MeshBasicMaterial;
    vm.opacity = v;
    verdict.current.scale.setScalar(STACK_SCALE * (0.94 + 0.06 * v));
    verdict.current.visible = v > 0.001;

    // Slow idle drift while scattered, plus a small pointer parallax.
    const drift = 1 - p;
    const targetY = Math.sin(t * 0.12) * 0.25 * drift + state.pointer.x * 0.035;
    const targetX = Math.cos(t * 0.1) * 0.08 * drift - state.pointer.y * 0.035;
    group.current.rotation.y += (targetY - group.current.rotation.y) * 0.05;
    group.current.rotation.x += (targetX - group.current.rotation.x) * 0.05;
  });

  return (
    <group ref={group}>
      <instancedMesh ref={mesh} args={[geometry, material, COUNT]} renderOrder={1} frustumCulled={false} />
      <mesh ref={verdict} renderOrder={2} position={[0, 0, 0.02]}>
        <planeGeometry args={[CARD_W, CARD_H]} />
        <meshBasicMaterial map={texture} transparent opacity={0} depthWrite={false} toneMapped={false} />
      </mesh>
    </group>
  );
}

export default function EvidenceScene({
  progress,
  active,
  onReady,
  onFallback,
}: {
  progress: MotionValue<number>;
  active: boolean;
  onReady: () => void;
  onFallback: () => void;
}) {
  const [dpr, setDpr] = useState(1.5);
  return (
    <Canvas
      dpr={dpr}
      frameloop={active ? 'always' : 'never'}
      camera={{ position: [0, 0, 9], fov: 38 }}
      gl={{ antialias: false, alpha: true, powerPreference: 'high-performance' }}
      onCreated={() => requestAnimationFrame(onReady)}
      aria-hidden
    >
      <PerformanceMonitor
        onDecline={() => setDpr(1)}
        onIncline={() => setDpr(1.75)}
        flipflops={3}
        onFallback={onFallback}
      />
      <Convergence progress={progress} />
    </Canvas>
  );
}
