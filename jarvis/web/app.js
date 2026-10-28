// Interface do J.A.R.V.I.S.: núcleo 3D, HUD e espectro que reagem à voz, com brilho cinematográfico.
import * as THREE from "three";
import { EffectComposer } from "./jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "./jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "./jsm/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "./jsm/postprocessing/OutputPass.js";
import { abrirArea, atualizarArea } from "./areas.js";

// ---------- Renderizador, câmera e pós-processamento ----------
const canvas = document.getElementById("cena");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
renderer.setClearColor(0x000000, 1);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const cena = new THREE.Scene();
cena.fog = new THREE.FogExp2(0x000000, 0.045);
const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200);
camera.position.set(0, 0, 6);

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(cena, camera));
const brilhoPos = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.8, 0.55, 0.22);
composer.addPass(brilhoPos);
composer.addPass(new OutputPass());

const uniformes = {
  uTempo: { value: 0 }, uGrave: { value: 0 }, uMedio: { value: 0 }, uAtividade: { value: 0 },
  uPixel: { value: 1 }, uLuz: { value: 0.7 },
};

let distanciaBase = 6;
function redimensionar() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  composer.setSize(w, h);
  brilhoPos.resolution.set(w, h);
  camera.aspect = w / h;
  distanciaBase = 6 / Math.min(1, camera.aspect * 0.95);
  camera.updateProjectionMatrix();
  uniformes.uPixel.value = renderer.getPixelRatio() * h / 820;
}

// ---------- Ruído para os shaders ----------
const RUIDO = /* glsl */ `
vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(1.0/6.0,1.0/3.0); const vec4 D=vec4(0.0,0.5,1.0,2.0);
  vec3 i=floor(v+dot(v,C.yyy)); vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz); vec3 l=1.0-g; vec3 i1=min(g.xyz,l.zxy); vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx; vec3 x2=x0-i2+C.yyy; vec3 x3=x0-D.yyy;
  i=mod289(i);
  vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
  float n_=0.142857142857; vec3 ns=n_*D.wyz-D.xzx;
  vec4 j=p-49.0*floor(p*ns.z*ns.z); vec4 x_=floor(j*ns.z); vec4 y_=floor(j-7.0*x_);
  vec4 x=x_*ns.x+ns.yyyy; vec4 y=y_*ns.x+ns.yyyy; vec4 h=1.0-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy); vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.0+1.0; vec4 s1=floor(b1)*2.0+1.0; vec4 sh=-step(h,vec4(0.0));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy; vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x); vec3 p1=vec3(a0.zw,h.y); vec3 p2=vec3(a1.xy,h.z); vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
  p0*=norm.x; p1*=norm.y; p2*=norm.z; p3*=norm.w;
  vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0); m=m*m;
  return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
}`;

const aditivo = { transparent: true, depthWrite: false, blending: THREE.AdditiveBlending };
const nucleo = new THREE.Group();
cena.add(nucleo);

// ---------- Esfera de partículas ----------
function esferaFibonacci(quantidade) {
  const pos = new Float32Array(quantidade * 3), aleatorio = new Float32Array(quantidade);
  const ouro = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < quantidade; i++) {
    const y = 1 - (i / (quantidade - 1)) * 2, r = Math.sqrt(1 - y * y), t = ouro * i;
    pos.set([Math.cos(t) * r, y, Math.sin(t) * r], i * 3);
    aleatorio[i] = Math.random();
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("aAleatorio", new THREE.BufferAttribute(aleatorio, 1));
  return g;
}

const particulas = new THREE.Points(esferaFibonacci(14000), new THREE.ShaderMaterial({
  ...aditivo,
  uniforms: uniformes,
  vertexShader: /* glsl */ `
    ${RUIDO}
    uniform float uTempo, uGrave, uMedio, uAtividade, uPixel;
    attribute float aAleatorio;
    varying float vBrilho;
    void main() {
      vec3 dir = normalize(position);
      float n1 = snoise(dir * 1.6 + vec3(uTempo * 0.2));
      float n2 = snoise(dir * 4.0 - vec3(uTempo * 0.5));
      float desloc = n1 * (0.045 + uGrave * 0.3 + uAtividade * 0.04) + n2 * (0.012 + uMedio * 0.1) + uGrave * 0.08;
      vec4 mv = modelViewMatrix * vec4(dir * (1.0 + desloc), 1.0);
      gl_Position = projectionMatrix * mv;
      gl_PointSize = (1.1 + aAleatorio * 1.5 + uGrave * 1.1) * uPixel * (6.0 / -mv.z);
      // Partículas da frente mais fortes que as de trás: dá profundidade.
      float frente = smoothstep(-1.2, 1.0, (modelViewMatrix * vec4(dir, 0.0)).z + 0.2);
      vBrilho = (0.3 + max(desloc, 0.0) * 1.8 + uAtividade * 0.18 + aAleatorio * 0.1) * (0.35 + 0.65 * frente);
    }`,
  fragmentShader: /* glsl */ `
    uniform float uLuz;
    varying float vBrilho;
    void main() {
      float d = length(gl_PointCoord - 0.5);
      if (d > 0.5) discard;
      gl_FragColor = vec4(vec3(vBrilho * uLuz), smoothstep(0.5, 0.0, d));
    }`,
}));
nucleo.add(particulas);

// ---------- Núcleo de cristal com borda luminosa ----------
const materialCristal = new THREE.ShaderMaterial({
  ...aditivo,
  uniforms: { ...uniformes },
  vertexShader: /* glsl */ `
    varying vec3 vNormal; varying vec3 vVista;
    void main() {
      vec4 mv = modelViewMatrix * vec4(position, 1.0);
      vNormal = normalize(normalMatrix * normal);
      vVista = normalize(-mv.xyz);
      gl_Position = projectionMatrix * mv;
    }`,
  fragmentShader: /* glsl */ `
    uniform float uGrave, uAtividade;
    varying vec3 vNormal; varying vec3 vVista;
    void main() {
      float fresnel = pow(1.0 - abs(dot(vNormal, vVista)), 2.2);
      float forca = fresnel * (0.4 + uGrave * 0.6 + uAtividade * 0.2) + 0.02;
      gl_FragColor = vec4(vec3(forca), 1.0);
    }`,
});
const cristal = new THREE.Mesh(new THREE.IcosahedronGeometry(0.36, 1), materialCristal);
const arestasCristal = new THREE.LineSegments(
  new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(0.37, 1)),
  new THREE.LineBasicMaterial({ color: 0xffffff, ...aditivo, opacity: 0.35 })
);
nucleo.add(cristal, arestasCristal);

// Casca geodésica externa
const casca = new THREE.LineSegments(
  new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(1.26, 2)),
  new THREE.LineBasicMaterial({ color: 0xffffff, ...aditivo, opacity: 0.045 })
);
nucleo.add(casca);

// ---------- HUD (anéis voltados para a câmera) ----------
const hud = new THREE.Group();
cena.add(hud);
const materialHud = (opacidade) => new THREE.LineBasicMaterial({ color: 0xffffff, ...aditivo, opacity: opacidade });

function arco(raio, inicio, fim, opacidade, segmentos = 96) {
  const pontos = [];
  for (let i = 0; i <= segmentos; i++) {
    const a = inicio + (fim - inicio) * (i / segmentos);
    pontos.push(new THREE.Vector3(Math.cos(a) * raio, Math.sin(a) * raio, 0));
  }
  return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pontos), materialHud(opacidade));
}

function anelDeMarcas(raio, quantidade, curta, longa, cadaLonga, opacidade) {
  const pos = [];
  for (let i = 0; i < quantidade; i++) {
    const a = (i / quantidade) * Math.PI * 2, tam = i % cadaLonga === 0 ? longa : curta;
    pos.push(Math.cos(a) * raio, Math.sin(a) * raio, 0, Math.cos(a) * (raio + tam), Math.sin(a) * (raio + tam), 0);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  return new THREE.LineSegments(g, materialHud(opacidade));
}

const camadasHud = [];
function camada(objetos, velocidade) {
  const grupo = new THREE.Group();
  objetos.forEach((o) => grupo.add(o));
  grupo.userData.velocidade = velocidade;
  camadasHud.push(grupo);
  hud.add(grupo);
  return grupo;
}
const TAU = Math.PI * 2;
camada([anelDeMarcas(1.62, 180, 0.025, 0.07, 15, 0.35)], 0.03);
camada([arco(1.8, 0, TAU * 0.2, 0.55), arco(1.8, TAU * 0.33, TAU * 0.5, 0.55), arco(1.8, TAU * 0.6, TAU * 0.9, 0.55)], -0.12);
camada([arco(1.9, 0, TAU, 0.1, 256)], 0);
camada([arco(2.06, 0, TAU * 0.12, 0.8), arco(2.06, TAU * 0.5, TAU * 0.62, 0.8)], 0.22);
camada([anelDeMarcas(2.18, 72, 0.02, 0.02, 1, 0.22)], -0.05);
camada([arco(2.45, TAU * 0.05, TAU * 0.2, 0.25), arco(2.45, TAU * 0.55, TAU * 0.7, 0.25)], -0.02);

// Espectro de áudio em volta da esfera
const BARRAS = 120;
const espectro = new THREE.InstancedMesh(
  new THREE.PlaneGeometry(0.014, 1).translate(0, 0.5, 0),
  new THREE.MeshBasicMaterial({ color: 0xffffff, ...aditivo, opacity: 0.85, side: THREE.DoubleSide }),
  BARRAS
);
hud.add(espectro);
const alturas = new Float32Array(BARRAS);
const auxiliar = new THREE.Object3D();
function atualizarEspectro(valores) {
  for (let i = 0; i < BARRAS; i++) {
    alturas[i] += (valores[i] - alturas[i]) * 0.35;
    const a = (i / BARRAS) * TAU + Math.PI / 2;
    auxiliar.position.set(Math.cos(a) * 1.36, Math.sin(a) * 1.36, 0);
    auxiliar.rotation.set(0, 0, a - Math.PI / 2);
    auxiliar.scale.set(1, 0.015 + alturas[i] * 0.22, 1);
    auxiliar.updateMatrix();
    espectro.setMatrixAt(i, auxiliar.matrix);
  }
  espectro.instanceMatrix.needsUpdate = true;
}

// Anéis orbitais em 3D
const orbitas = [];
[[2.3, 1.15, 0.25], [2.6, -1.0, -0.4]].forEach(([raio, rx, rz], i) => {
  const linha = arco(raio, 0, TAU, 0.18, 256);
  linha.rotation.set(rx, 0, rz);
  const satelite = new THREE.Mesh(new THREE.SphereGeometry(0.016, 12, 12), new THREE.MeshBasicMaterial({ color: 0xffffff }));
  const grupo = new THREE.Group();
  grupo.add(linha);
  grupo.userData = { raio, satelite, velocidade: (i ? -1 : 1) * (0.25 + i * 0.1), linha };
  linha.add(satelite);
  cena.add(grupo);
  orbitas.push(grupo);
});

// Campo de estrelas com profundidade
const estrelas = (() => {
  const n = 2200, pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const v = new THREE.Vector3().randomDirection().multiplyScalar(6 + Math.random() * 40);
    pos.set([v.x, v.y, v.z], i * 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  return new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffffff, size: 0.05, ...aditivo, opacity: 0.55 }));
})();
cena.add(estrelas);

// Ondas de choque nas batidas de grave
const ondas = [];
function dispararOnda(forca) {
  const onda = new THREE.Mesh(new THREE.RingGeometry(0.99, 1.0, 160),
    new THREE.MeshBasicMaterial({ color: 0xffffff, ...aditivo, opacity: 0.5 * forca }));
  onda.userData = { idade: 0, forca };
  ondas.push(onda);
  hud.add(onda);
}

// ---------- Áudio ----------
let contexto = null, analisador = null, entrada = null, dadosFreq = null, fonteAtual = null;
let simulacaoAte = 0, efeitoVoz = true;

function respostaAoImpulso(ctx, segundos, decaimento) {
  const tamanho = Math.floor(ctx.sampleRate * segundos);
  const buffer = ctx.createBuffer(2, tamanho, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const dados = buffer.getChannelData(c);
    for (let i = 0; i < tamanho; i++) dados[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / tamanho, decaimento);
  }
  return buffer;
}

function prepararAudio() {
  if (contexto) return;
  contexto = new (window.AudioContext || window.webkitAudioContext)();
  analisador = contexto.createAnalyser();
  analisador.fftSize = 2048;
  analisador.smoothingTimeConstant = 0.6;
  dadosFreq = new Uint8Array(analisador.frequencyBinCount);
  const saida = contexto.createGain();
  saida.connect(analisador).connect(contexto.destination);

  const compressor = contexto.createDynamicsCompressor();
  compressor.threshold.value = -20;
  compressor.ratio.value = 3;
  const corpo = contexto.createBiquadFilter();
  corpo.type = "lowshelf"; corpo.frequency.value = 170; corpo.gain.value = 3;
  entrada = contexto.createBiquadFilter();
  entrada.type = "highpass"; entrada.frequency.value = 75;

  if (efeitoVoz) {
    // "Efeito JARVIS": presença nítida, leve dobra metálica e ambiente curto de sala.
    const presenca = contexto.createBiquadFilter();
    presenca.type = "peaking"; presenca.frequency.value = 3200; presenca.Q.value = 0.8; presenca.gain.value = 3.5;
    entrada.connect(corpo).connect(presenca).connect(compressor);
    compressor.connect(saida);
    const dobra = contexto.createDelay(0.05);
    dobra.delayTime.value = 0.011;
    const ganhoDobra = contexto.createGain();
    ganhoDobra.gain.value = 0.2;
    compressor.connect(dobra).connect(ganhoDobra).connect(saida);
    const sala = contexto.createConvolver();
    sala.buffer = respostaAoImpulso(contexto, 0.45, 3.2);
    const ganhoSala = contexto.createGain();
    ganhoSala.gain.value = 0.13;
    compressor.connect(sala).connect(ganhoSala).connect(saida);
  } else {
    entrada.connect(corpo).connect(compressor).connect(saida);
  }
}

function base64ParaBuffer(b64) {
  const bin = atob(b64), bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

const avisarFimDaFala = () => api()?.audio_terminou();

async function tocar(b64) {
  prepararAudio();
  if (contexto.state === "suspended") await contexto.resume();
  try {
    const buffer = await contexto.decodeAudioData(base64ParaBuffer(b64));
    fonteAtual?.stop();
    const fonte = contexto.createBufferSource();
    fonte.buffer = buffer;
    fonte.connect(entrada);
    fonte.onended = () => { if (fonteAtual === fonte) fonteAtual = null; avisarFimDaFala(); };
    fonteAtual = fonte;
    fonte.start();
  } catch (erro) {
    console.error("Falha ao tocar a fala", erro);
    avisarFimDaFala();
  }
}

let graveSuave = 0, medioSuave = 0, mediaLenta = 0, ultimaBatida = 0, tremor = 0;
const valoresEspectro = new Float32Array(BARRAS);

function lerAudio(t) {
  let grave = 0, medio = 0;
  const falandoDeVerdade = analisador && fonteAtual;
  if (falandoDeVerdade) {
    analisador.getByteFrequencyData(dadosFreq);
    const hzPorBin = contexto.sampleRate / analisador.fftSize;
    const faixa = (de, ate) => {
      const a = Math.max(1, Math.floor(de / hzPorBin)), b = Math.ceil(ate / hzPorBin);
      let s = 0;
      for (let i = a; i <= b; i++) s += dadosFreq[i];
      return s / ((b - a + 1) * 255);
    };
    grave = Math.min(1, Math.pow(faixa(50, 260), 1.4) * 1.7);
    medio = Math.min(1, faixa(260, 2200) * 1.4);
    // Espectro espelhado (escala logarítmica de 70 Hz a 7 kHz).
    const metade = BARRAS / 2;
    for (let i = 0; i < metade; i++) {
      const de = 70 * Math.pow(100, i / metade), ate = 70 * Math.pow(100, (i + 1) / metade);
      const v = Math.min(1, faixa(de, ate) * 1.6);
      valoresEspectro[i] = v;
      valoresEspectro[BARRAS - 1 - i] = v;
    }
  } else {
    const simulando = t < simulacaoAte;
    if (simulando) {
      grave = 0.25 + 0.35 * Math.abs(Math.sin(t * 9.5) * Math.sin(t * 3.1));
      medio = grave * 0.8;
    }
    for (let i = 0; i < BARRAS; i++) {
      const onda = 0.08 + 0.06 * Math.sin(t * 2 + i * 0.35) * Math.sin(t * 0.7 + i * 0.11);
      valoresEspectro[i] = simulando ? grave * (0.5 + 0.5 * Math.sin(i * 0.7 + t * 12)) : onda * (0.4 + atividade);
    }
  }
  graveSuave += (grave - graveSuave) * (grave > graveSuave ? 0.55 : 0.12);
  medioSuave += (medio - medioSuave) * (medio > medioSuave ? 0.5 : 0.1);
  mediaLenta += (grave - mediaLenta) * 0.03;
  if (grave - mediaLenta > 0.14 && t - ultimaBatida > 0.22) {
    ultimaBatida = t;
    dispararOnda(Math.min(1, 0.5 + grave));
    tremor = Math.min(0.05, 0.015 + grave * 0.035);
  }
}

// ---------- Estados ----------
const ESTADOS = {
  iniciando: { rotulo: "inicializando", luz: 0.55, atividade: 0.2, giro: 0.3, brilho: 0.8 },
  ocioso:    { rotulo: "aguardando", luz: 0.7, atividade: 0.0, giro: 0.06, brilho: 0.8 },
  ouvindo:   { rotulo: "ouvindo", luz: 0.95, atividade: 0.75, giro: 0.1, brilho: 1.0 },
  pensando:  { rotulo: "processando", luz: 0.6, atividade: 0.5, giro: 0.6, brilho: 0.9 },
  mudo:      { rotulo: "microfone desligado", luz: 0.35, atividade: 0.0, giro: 0.03, brilho: 0.55 },
  falando:   { rotulo: "falando", luz: 0.8, atividade: 0.35, giro: 0.12, brilho: 0.85 },
};
let estado = ESTADOS.iniciando, atividade = 0.2, giro = 0.3;

const $ = (id) => document.getElementById(id);
const elEstado = $("estado"), elFala = $("fala"), elVoce = $("voce"), elConfirmacao = $("confirmacao");

// ---------- Animação ----------
const relogio = new THREE.Clock();
const mouse = new THREE.Vector2(), olhar = new THREE.Vector2();
window.addEventListener("pointermove", (e) => {
  mouse.set(e.clientX / window.innerWidth - 0.5, e.clientY / window.innerHeight - 0.5);
});

function quadro() {
  const dt = Math.min(relogio.getDelta(), 0.05), t = relogio.elapsedTime;
  lerAudio(t);

  atividade += (estado.atividade - atividade) * 0.05;
  giro += (estado.giro - giro) * 0.04;
  uniformes.uLuz.value += (estado.luz - uniformes.uLuz.value) * 0.05;
  brilhoPos.strength += (estado.brilho + graveSuave * 0.25 - brilhoPos.strength) * 0.1;
  uniformes.uTempo.value = t;
  uniformes.uGrave.value = graveSuave;
  uniformes.uMedio.value = medioSuave;
  uniformes.uAtividade.value = atividade;

  const respiracao = estado === ESTADOS.ouvindo ? 0.035 * Math.sin(t * 4) : 0.012 * Math.sin(t * 1.3);
  nucleo.rotation.y += dt * giro;
  nucleo.rotation.x = Math.sin(t * 0.2) * 0.15;
  nucleo.scale.setScalar(1 + respiracao + graveSuave * 0.07);
  cristal.rotation.x -= dt * (0.3 + giro);
  cristal.rotation.z += dt * 0.2;
  arestasCristal.rotation.copy(cristal.rotation);
  cristal.scale.setScalar(1 + graveSuave * 0.2);
  arestasCristal.scale.copy(cristal.scale);
  casca.rotation.y -= dt * giro * 0.5;
  casca.material.opacity = 0.04 + graveSuave * 0.12 + atividade * 0.03;

  // HUD sempre de frente para a câmera, com leve inclinação pela posição do mouse.
  hud.quaternion.copy(camera.quaternion);
  hud.scale.setScalar(1 + graveSuave * 0.04);
  camadasHud.forEach((c) => { c.rotation.z += dt * c.userData.velocidade * (1 + atividade * 2.5 + graveSuave * 3); });
  atualizarEspectro(valoresEspectro);

  orbitas.forEach((o, i) => {
    o.rotation.y += dt * 0.05 * (i ? -1 : 1);
    const a = t * o.userData.velocidade;
    o.userData.satelite.position.set(Math.cos(a) * o.userData.raio, Math.sin(a) * o.userData.raio, 0);
  });
  estrelas.rotation.y += dt * 0.004;

  for (let i = ondas.length - 1; i >= 0; i--) {
    const onda = ondas[i];
    onda.userData.idade += dt;
    const p = onda.userData.idade / 0.9;
    onda.scale.setScalar(1.05 + p * 1.4);
    onda.material.opacity = (1 - p) * 0.25 * onda.userData.forca;
    if (p >= 1) {
      hud.remove(onda);
      onda.geometry.dispose();
      onda.material.dispose();
      ondas.splice(i, 1);
    }
  }

  // Câmera com paralaxe suave + tremor nas batidas.
  olhar.lerp(mouse, 0.04);
  tremor *= 0.88;
  camera.position.set(
    olhar.x * 1.2 + (Math.random() - 0.5) * tremor,
    -olhar.y * 0.8 + (Math.random() - 0.5) * tremor,
    distanciaBase
  );
  camera.lookAt(0, -0.35, 0);

  composer.render();
  requestAnimationFrame(quadro);
}

// ---------- Painéis ----------
function atualizarRelogio() {
  const agora = new Date();
  $("relogio").textContent = agora.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  $("data").textContent = agora.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" });
}

async function atualizarSistema() {
  try {
    const s = await api()?.sistema();
    if (!s) return;
    for (const chave of ["cpu", "memoria", "disco", "bateria"]) {
      if (s[chave] === null || s[chave] === undefined) {
        if (chave === "bateria") $("m-bateria").style.display = "none";
        continue;
      }
      $(`v-${chave}`).textContent = `${Math.round(s[chave])}%${chave === "bateria" && s.carregando ? " ⚡" : ""}`;
      $(`b-${chave}`).style.width = `${s[chave]}%`;
    }
  } catch { /* interface aberta fora do app */ }
}

let interacoes = 0;
function registrar(quem, texto) {
  const lista = $("registro");
  lista.querySelector(".vazio")?.remove();
  const ultimo = lista.lastElementChild;
  if (quem === "jarvis+" && ultimo?.classList.contains("jarvis")) {
    ultimo.lastChild.textContent += " " + texto;
    return;
  }
  const item = document.createElement("li");
  item.className = quem === "voce" ? "voce" : "jarvis";
  const hora = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  item.innerHTML = `<small>${quem === "voce" ? "Você" : "Jarvis"} · ${hora}</small>`;
  item.append(document.createTextNode(texto));
  lista.append(item);
  while (lista.children.length > 7) lista.firstElementChild.remove();
  if (quem === "voce") $("contador").textContent = String(++interacoes).padStart(2, "0");
}

// ---------- Ligação com o Python ----------
function api() {
  return window.pywebview?.api;
}

let iniciado = false;
function iniciar() {
  if (iniciado) return;
  iniciado = true;
  $("inicio").classList.add("sumindo");
  api()?.iniciar();
}

// ---------- Microfone e modo de resposta ----------
let mudo = false;
function mostrarMudo(valor) {
  mudo = valor;
  $("microfone").classList.toggle("mudo", mudo);
  $("microfone").title = mudo ? "Voltar a ouvir (Ctrl+M)" : "Parar de ouvir (Ctrl+M)";
}
function alternarMicrofone() {
  mostrarMudo(!mudo);
  api()?.definir_mudo(mudo);
}
$("microfone").addEventListener("click", alternarMicrofone);
window.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key.toLowerCase() === "m") { e.preventDefault(); alternarMicrofone(); }
});

function mostrarModo(modo) {
  document.querySelectorAll(".modos button").forEach((b) => b.classList.toggle("ativo", b.dataset.modo === modo));
  try { localStorage.setItem("jarvis-modo", modo); } catch { /* sem armazenamento */ }
}
document.querySelectorAll(".modos button").forEach((botao) => {
  botao.addEventListener("click", () => { mostrarModo(botao.dataset.modo); api()?.definir_modo(botao.dataset.modo); });
});

async function aoFicarPronto() {
  try {
    const cfg = await api()?.configuracao();
    if (cfg) efeitoVoz = cfg.efeitoVoz;
    let modo = cfg?.modo || "curta";
    try { modo = localStorage.getItem("jarvis-modo") || modo; } catch { /* sem armazenamento */ }
    mostrarModo(modo);
    api()?.definir_modo(modo);
  } catch { /* usa o padrão */ }
  prepararAudio();
  try { await contexto.resume(); } catch { /* sem permissão ainda */ }
  // Se o navegador deixou tocar áudio sozinho, já inicia; senão, pede um clique.
  if (contexto.state === "running") iniciar();
  else $("inicio").classList.add("visivel");
  atualizarSistema();
  setInterval(atualizarSistema, 2000);
}

$("inicio").addEventListener("click", async () => {
  prepararAudio();
  await contexto.resume();
  iniciar();
});

document.querySelectorAll(".controles button").forEach((botao) => {
  botao.addEventListener("click", () => api()?.[botao.dataset.acao]?.());
});

$("barra").addEventListener("submit", (e) => {
  e.preventDefault();
  const campo = $("entrada"), texto = campo.value.trim();
  if (!texto) return;
  campo.value = "";
  elConfirmacao.classList.remove("ativa");
  if (!iniciado) { prepararAudio(); contexto.resume(); iniciar(); }
  api()?.enviar(texto);
});

elConfirmacao.addEventListener("click", (e) => {
  const resposta = e.target.dataset?.resposta;
  if (!resposta) return;
  elConfirmacao.classList.remove("ativa");
  api()?.enviar(resposta);
});

// Funções chamadas pelo Python (app.py).
window.jarvis = {
  falar: tocar,
  falarSemAudio(segundos) { simulacaoAte = relogio.elapsedTime + segundos; },
  estado(nome) {
    estado = ESTADOS[nome] || ESTADOS.ocioso;
    elEstado.textContent = estado.rotulo;
    if (nome === "pensando" || nome === "ocioso") elConfirmacao.classList.remove("ativa");
  },
  mensagem(quem, texto) {
    registrar(quem, texto);
    if (quem === "jarvis+" && elFala.textContent.length + texto.length < 220) {
      const trecho = document.createElement("span");
      trecho.textContent = " " + texto;
      trecho.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 300 });
      elFala.append(trecho);
      return;
    }
    const el = quem === "voce" ? elVoce : elFala;
    el.animate([{ opacity: 0, transform: "translateY(6px)" }, { opacity: 1, transform: "none" }], { duration: 350 });
    el.textContent = quem === "voce" ? `“${texto}”` : texto;
  },
  confirmar() { elConfirmacao.classList.add("ativa"); },
  tempos(texto) { $("tempos").textContent = texto; },
  abrirArea,
  atualizarArea,
  modo: mostrarModo,
  mudo: mostrarMudo,
};

window.addEventListener("resize", redimensionar);
redimensionar();
atualizarRelogio();
setInterval(atualizarRelogio, 1000);
quadro();
if (window.pywebview?.api) aoFicarPronto();
else window.addEventListener("pywebviewready", aoFicarPronto, { once: true });
