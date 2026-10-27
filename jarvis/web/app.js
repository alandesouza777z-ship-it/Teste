// Interface do J.A.R.V.I.S.: esfera 3D de partículas que reage aos graves da voz.
import * as THREE from "./three.module.min.js";

// ---------- Cena ----------
const canvas = document.getElementById("cena");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setClearColor(0x000000, 1);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const cena = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
const nucleo = new THREE.Group();
cena.add(nucleo);

function redimensionar() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  // Em janelas estreitas, afasta a câmera para a esfera caber.
  camera.position.z = 4.6 / Math.min(1, camera.aspect * 1.1);
  camera.updateProjectionMatrix();
  uniformes.uPixel.value = renderer.getPixelRatio() * h / 800;
}

// ---------- Esfera de partículas (shader com ruído) ----------
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

const uniformes = {
  uTempo: { value: 0 },
  uGrave: { value: 0 },
  uMedio: { value: 0 },
  uAtividade: { value: 0 },
  uPixel: { value: 1 },
  uCor: { value: new THREE.Color("#a0a0a0") },
  uCor2: { value: new THREE.Color("#ffffff") },
};

function esferaFibonacci(quantidade) {
  const posicoes = new Float32Array(quantidade * 3);
  const aleatorio = new Float32Array(quantidade);
  const ouro = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < quantidade; i++) {
    const y = 1 - (i / (quantidade - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const t = ouro * i;
    posicoes.set([Math.cos(t) * r, y, Math.sin(t) * r], i * 3);
    aleatorio[i] = Math.random();
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(posicoes, 3));
  g.setAttribute("aAleatorio", new THREE.BufferAttribute(aleatorio, 1));
  return g;
}

const particulas = new THREE.Points(
  esferaFibonacci(12000),
  new THREE.ShaderMaterial({
    uniforms: uniformes,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */ `
      ${RUIDO}
      uniform float uTempo, uGrave, uMedio, uAtividade, uPixel;
      attribute float aAleatorio;
      varying float vBrilho;
      void main() {
        vec3 dir = normalize(position);
        float n1 = snoise(dir * 1.7 + vec3(uTempo * 0.22));
        float n2 = snoise(dir * 4.2 - vec3(uTempo * 0.55));
        float desloc = n1 * (0.05 + uGrave * 0.3 + uAtividade * 0.04)
                     + n2 * (0.015 + uMedio * 0.1)
                     + uGrave * 0.08;
        vec4 mv = modelViewMatrix * vec4(dir * (1.0 + desloc), 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = (1.3 + aAleatorio * 1.7 + uGrave * 2.6) * uPixel * (4.6 / -mv.z);
        vBrilho = 0.5 + max(desloc, 0.0) * 3.0 + uAtividade * 0.22 + aAleatorio * 0.12;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uCor, uCor2;
      varying float vBrilho;
      void main() {
        float d = length(gl_PointCoord - 0.5);
        if (d > 0.5) discard;
        float alfa = smoothstep(0.5, 0.0, d);
        vec3 cor = mix(uCor, uCor2, clamp(vBrilho - 0.45, 0.0, 1.0));
        gl_FragColor = vec4(cor * vBrilho, alfa);
      }`,
  })
);
nucleo.add(particulas);

// Brilho central
function texturaBrilho() {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
  g.addColorStop(0, "rgba(255,255,255,0.32)");
  g.addColorStop(0.25, "rgba(200,200,200,0.12)");
  g.addColorStop(0.6, "rgba(120,120,120,0.04)");
  g.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 256, 256);
  return new THREE.CanvasTexture(c);
}
const brilho = new THREE.Sprite(new THREE.SpriteMaterial({
  map: texturaBrilho(), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true,
}));
brilho.scale.setScalar(3.4);
cena.add(brilho);

// Casca geométrica
const casca = new THREE.LineSegments(
  new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(1.32, 2)),
  new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.06, blending: THREE.AdditiveBlending, depthWrite: false })
);
nucleo.add(casca);

// Anéis orbitais tracejados
const aneis = [];
[[1.62, 0.35, 0.0], [1.78, -0.5, 0.6], [1.95, 1.2, -0.3]].forEach(([raio, rx, rz], i) => {
  const pontos = [];
  for (let k = 0; k <= 256; k++) {
    const a = (k / 256) * Math.PI * 2;
    pontos.push(new THREE.Vector3(Math.cos(a) * raio, Math.sin(a) * raio, 0));
  }
  const linha = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(pontos),
    new THREE.LineDashedMaterial({
      color: 0xffffff, dashSize: 0.06 + i * 0.05, gapSize: 0.05 + i * 0.03,
      transparent: true, opacity: 0.32 - i * 0.07, blending: THREE.AdditiveBlending, depthWrite: false,
    })
  );
  linha.computeLineDistances();
  linha.rotation.set(rx, 0, rz);
  linha.userData.velocidade = (i % 2 ? -1 : 1) * (0.08 + i * 0.05);
  aneis.push(linha);
  cena.add(linha);
});

// Poeira ao fundo
const poeira = (() => {
  const n = 700, pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const v = new THREE.Vector3().randomDirection().multiplyScalar(2.4 + Math.random() * 5);
    pos.set([v.x, v.y, v.z], i * 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  return new THREE.Points(g, new THREE.PointsMaterial({
    color: 0x9a9a9a, size: 0.018, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false,
  }));
})();
cena.add(poeira);

// Ondas de choque disparadas pelas batidas de grave
const ondas = [];
function dispararOnda(forca) {
  const onda = new THREE.Mesh(
    new THREE.RingGeometry(0.985, 1.0, 128),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.5 * forca, blending: THREE.AdditiveBlending, depthWrite: false })
  );
  onda.userData = { idade: 0, forca };
  ondas.push(onda);
  cena.add(onda);
}

// ---------- Áudio ----------
let contexto = null, analisador = null, dadosFreq = null;
let fonteAtual = null;
let simulacaoAte = 0;

function prepararAudio() {
  if (contexto) return;
  contexto = new (window.AudioContext || window.webkitAudioContext)();
  analisador = contexto.createAnalyser();
  analisador.fftSize = 2048;
  analisador.smoothingTimeConstant = 0.55;
  dadosFreq = new Uint8Array(analisador.frequencyBinCount);

  // Cadeia de efeitos: reforço de grave + compressor, para a voz soar mais encorpada.
  const grave = contexto.createBiquadFilter();
  grave.type = "lowshelf";
  grave.frequency.value = 180;
  grave.gain.value = 4;
  const compressor = contexto.createDynamicsCompressor();
  compressor.threshold.value = -18;
  compressor.ratio.value = 3;
  grave.connect(compressor).connect(analisador).connect(contexto.destination);
  analisador.userData = { entrada: grave };
}

function base64ParaBuffer(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

function avisarFimDaFala() {
  window.pywebview?.api?.audio_terminou();
}

async function tocar(b64) {
  prepararAudio();
  if (contexto.state === "suspended") await contexto.resume();
  try {
    const buffer = await contexto.decodeAudioData(base64ParaBuffer(b64));
    fonteAtual?.stop();
    const fonte = contexto.createBufferSource();
    fonte.buffer = buffer;
    fonte.connect(analisador.userData.entrada);
    fonte.onended = () => { if (fonteAtual === fonte) fonteAtual = null; avisarFimDaFala(); };
    fonteAtual = fonte;
    fonte.start();
  } catch (erro) {
    console.error("Falha ao tocar a fala", erro);
    avisarFimDaFala();
  }
}

let graveSuave = 0, medioSuave = 0, mediaLenta = 0, ultimaBatida = 0;

function lerAudio(t) {
  let grave = 0, medio = 0;
  if (analisador && fonteAtual) {
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
  } else if (t < simulacaoAte) {
    // Fala sem áudio analisável (voz offline): simula as sílabas.
    grave = 0.25 + 0.35 * Math.abs(Math.sin(t * 9.5) * Math.sin(t * 3.1));
    medio = grave * 0.8;
  }
  // Ataque rápido, queda suave.
  graveSuave += (grave - graveSuave) * (grave > graveSuave ? 0.55 : 0.12);
  medioSuave += (medio - medioSuave) * (medio > medioSuave ? 0.5 : 0.1);
  mediaLenta += (grave - mediaLenta) * 0.03;
  if (grave - mediaLenta > 0.14 && t - ultimaBatida > 0.22) {
    ultimaBatida = t;
    dispararOnda(Math.min(1, 0.5 + grave));
    tremor = Math.min(0.06, 0.02 + grave * 0.04);
  }
}

// ---------- Estados ----------
const ESTADOS = {
  ocioso:   { rotulo: "aguardando · diga “jarvis”", cor: "#a0a0a0", cor2: "#ffffff", atividade: 0.0, giro: 0.05 },
  ouvindo:  { rotulo: "ouvindo",                    cor: "#d0d0d0", cor2: "#ffffff", atividade: 0.7, giro: 0.08 },
  pensando: { rotulo: "processando",                cor: "#7a7a7a", cor2: "#e0e0e0", atividade: 0.45, giro: 0.45 },
  falando:  { rotulo: "falando",                    cor: "#b8b8b8", cor2: "#ffffff", atividade: 0.35, giro: 0.1 },
};
let estado = ESTADOS.ocioso;
const corAlvo = new THREE.Color(estado.cor), cor2Alvo = new THREE.Color(estado.cor2);
let atividade = 0, giro = 0.05, tremor = 0;

const elEstado = document.getElementById("estado");
const elFala = document.getElementById("fala");
const elVoce = document.getElementById("voce");
const elConfirmacao = document.getElementById("confirmacao");

// ---------- Animação ----------
const relogio = new THREE.Clock();
function quadro() {
  const dt = Math.min(relogio.getDelta(), 0.05);
  const t = relogio.elapsedTime;
  lerAudio(t);

  atividade += (estado.atividade - atividade) * 0.05;
  giro += (estado.giro - giro) * 0.04;
  uniformes.uCor.value.lerp(corAlvo, 0.05);
  uniformes.uCor2.value.lerp(cor2Alvo, 0.05);

  const respiracao = estado === ESTADOS.ouvindo ? 0.04 * Math.sin(t * 4) : 0.015 * Math.sin(t * 1.3);
  uniformes.uTempo.value = t;
  uniformes.uGrave.value = graveSuave;
  uniformes.uMedio.value = medioSuave;
  uniformes.uAtividade.value = atividade;

  nucleo.rotation.y += dt * giro;
  nucleo.rotation.x = Math.sin(t * 0.2) * 0.15;
  nucleo.scale.setScalar(1 + respiracao + graveSuave * 0.07);
  casca.rotation.y -= dt * giro * 0.6;
  casca.material.opacity = 0.05 + graveSuave * 0.18 + atividade * 0.04;

  brilho.scale.setScalar(3.2 + graveSuave * 1.4 + atividade * 0.4);
  brilho.material.opacity = 0.75 + graveSuave * 0.25;
  brilho.material.color.copy(uniformes.uCor2.value);

  aneis.forEach((anel, i) => {
    anel.rotation.z += dt * anel.userData.velocidade * (1 + atividade * 2 + graveSuave * 4);
    anel.scale.setScalar(1 + graveSuave * (0.04 + i * 0.02));
    anel.material.color.copy(uniformes.uCor.value).lerp(uniformes.uCor2.value, 0.3);
  });
  poeira.rotation.y += dt * 0.01;

  for (let i = ondas.length - 1; i >= 0; i--) {
    const onda = ondas[i];
    onda.userData.idade += dt;
    const p = onda.userData.idade / 0.9;
    onda.scale.setScalar(1.05 + p * 1.3);
    onda.material.opacity = (1 - p) * 0.45 * onda.userData.forca;
    onda.quaternion.copy(camera.quaternion);
    if (p >= 1) {
      cena.remove(onda);
      onda.geometry.dispose();
      onda.material.dispose();
      ondas.splice(i, 1);
    }
  }

  tremor *= 0.88;
  camera.position.x = (Math.random() - 0.5) * tremor;
  camera.position.y = (Math.random() - 0.5) * tremor;
  camera.lookAt(0, -0.32, 0);

  renderer.render(cena, camera);
  requestAnimationFrame(quadro);
}

// ---------- Interface ----------
function atualizarRelogio() {
  const agora = new Date();
  document.getElementById("relogio").textContent =
    agora.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  document.getElementById("data").textContent =
    agora.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" });
}

function api() {
  return window.pywebview?.api;
}

document.getElementById("inicio").addEventListener("click", (e) => {
  prepararAudio();
  contexto.resume();
  e.currentTarget.classList.add("sumindo");
  const iniciar = () => api()?.iniciar();
  if (api()) iniciar();
  else window.addEventListener("pywebviewready", iniciar, { once: true });
  document.getElementById("entrada").focus();
});

document.getElementById("barra").addEventListener("submit", (e) => {
  e.preventDefault();
  const entrada = document.getElementById("entrada");
  const texto = entrada.value.trim();
  if (!texto) return;
  entrada.value = "";
  elConfirmacao.classList.remove("ativa");
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
  falarSemAudio(segundos) {
    simulacaoAte = relogio.elapsedTime + segundos;
  },
  estado(nome) {
    estado = ESTADOS[nome] || ESTADOS.ocioso;
    corAlvo.set(estado.cor);
    cor2Alvo.set(estado.cor2);
    elEstado.textContent = estado.rotulo;
    if (nome === "pensando" || nome === "ocioso") elConfirmacao.classList.remove("ativa");
  },
  mensagem(quem, texto) {
    // "jarvis+" = próxima frase da mesma resposta: entra ao lado da anterior.
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
  confirmar() {
    elConfirmacao.classList.add("ativa");
  },
};

window.addEventListener("resize", redimensionar);
redimensionar();
atualizarRelogio();
setInterval(atualizarRelogio, 1000);
quadro();
