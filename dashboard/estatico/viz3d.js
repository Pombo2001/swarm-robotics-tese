/* Visualizador 3D de episódios, no browser.
 *
 * Porquê Canvas 2D e não three.js: o desenho é uma projeção isométrica de umas
 * dezenas de caixas e vinte esferas — não precisa de WebGL, e assim não há uma
 * biblioteca de 600 KB a vir de um CDN. Isso importa aqui: a cópia que corre no
 * Raspberry Pi tem de funcionar sem depender de rede externa, e a mesma página
 * serve as duas máquinas.
 *
 * A cena é desenhada de trás para a frente (pintor): cada face e cada agente
 * levam uma profundidade, ordena-se, pinta-se. Chega para o que se quer ver —
 * por onde o enxame passa, onde se amontoa, e se atravessa o que não devia.
 */
(function () {
  "use strict";

  const COR = {
    fundo: "#0b0e11", chao: "#12171c", contorno: "#38434d",
    paredeTopo: "#39434c", paredeLado: "#232a31", paredeLadoEscuro: "#1a2026",
    ninho: "#10b981", obst: "#7c5c3a", sombra: "rgba(0,0,0,.45)",
    GNN: "#2f9e44", PPO: "#e8590c", SAC: "#1c7ed6",
  };
  // As paredes reais têm 2×raio da arena (30 m nos sete cenários, 120 no mapa
  // grande) — é o que as torna estanques desde a correção de 29 jul. Desenhá-las
  // com essa altura tapava a cena inteira; corta-se ao VISUAL, e diz-se.
  const ALTURA_VISUAL = 2.2;

  function criar(canvas, dados, aoMudar) {
    const ctx = canvas.getContext("2d");
    const meta = dados.meta;
    const est = {
      quadro: 0, aPassar: true, velocidade: 1,
      az: -0.6, el: 0.62, zoom: 1, ultimo: 0,
    };

    function tamanho() {
      const r = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = r.width * dpr;
      canvas.height = r.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      return { w: r.width, h: r.height };
    }

    function projetor(w, h) {
      const cosA = Math.cos(est.az), sinA = Math.sin(est.az);
      const sinE = Math.sin(est.el), cosE = Math.cos(est.el);
      const escala = (Math.min(w, h) / (2.35 * meta.raio_arena)) * est.zoom;
      const cx = w / 2, cy = h / 2 + h * 0.10;
      return function (x, y, z) {
        const xr = x * cosA - y * sinA;
        const yr = x * sinA + y * cosA;
        return { x: cx + xr * escala, y: cy + (yr * sinE - z * cosE) * escala,
                 d: yr, e: escala };
      };
    }

    function faceCaixa(P, p, s, alt) {
      // 8 vértices; as faces guardam a profundidade média para a ordenação.
      const hx = s[0] / 2, hy = s[1] / 2;
      const z0 = 0, z1 = Math.min(alt, ALTURA_VISUAL);
      const v = [];
      for (const [dx, dy, dz] of [[-1,-1,0],[1,-1,0],[1,1,0],[-1,1,0],
                                  [-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]]) {
        v.push(P(p[0] + dx * hx, p[1] + dy * hy, dz ? z1 : z0));
      }
      const faces = [
        { i: [4,5,6,7], c: COR.paredeTopo },
        { i: [0,1,5,4], c: COR.paredeLado },
        { i: [1,2,6,5], c: COR.paredeLadoEscuro },
        { i: [2,3,7,6], c: COR.paredeLado },
        { i: [3,0,4,7], c: COR.paredeLadoEscuro },
      ];
      return faces.map(f => ({
        tipo: "poli", cor: f.c,
        pts: f.i.map(k => v[k]),
        d: f.i.reduce((a, k) => a + v[k].d, 0) / f.i.length,
      }));
    }

    function desenhar() {
      const { w, h } = tamanho();
      const P = projetor(w, h);
      ctx.fillStyle = COR.fundo;
      ctx.fillRect(0, 0, w, h);

      // Chão: o disco da arena (é uma esfera no simulador; vê-se o equador).
      const R = meta.raio_arena, N = 72, borda = [];
      for (let i = 0; i <= N; i++) {
        const a = (i / N) * Math.PI * 2;
        borda.push(P(R * Math.cos(a), R * Math.sin(a), 0));
      }
      ctx.beginPath();
      borda.forEach((q, i) => i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y));
      ctx.closePath();
      ctx.fillStyle = COR.chao; ctx.fill();
      ctx.strokeStyle = COR.contorno; ctx.lineWidth = 1; ctx.stroke();

      const itens = [];
      for (const p of dados.geometria.paredes) {
        itens.push(...faceCaixa(P, p.p, p.s, ALTURA_VISUAL));
      }
      for (const o of dados.geometria.obstaculos) {
        const q = P(o[0], o[1], 0);
        itens.push({ tipo: "circ", cor: COR.obst, x: q.x, y: q.y,
                     r: Math.max(1.5, meta.raio_obstaculo * q.e), d: q.d });
      }
      const ninho = dados.ninho[est.quadro] || dados.ninho[0];
      const qn = P(ninho[0], ninho[1], 0);
      itens.push({ tipo: "ninho", x: qn.x, y: qn.y,
                   r: Math.max(4, meta.raio_ninho * qn.e), d: qn.d });

      const cor = COR[meta.algo] || "#c9d1d9";
      for (const a of dados.quadros[est.quadro]) {
        const chao = P(a[0], a[1], 0);
        const q = P(a[0], a[1], a[2]);
        itens.push({ tipo: "agente", cor: cor, x: q.x, y: q.y,
                     r: Math.max(2.5, meta.raio_robo * q.e * 1.8),
                     sx: chao.x, sy: chao.y, d: q.d });
      }

      // Um agente desenhado ACIMA do topo da parede lê-se como um agente a
      // passar por cima dela — e foi exatamente isso que aconteceu de facto até
      // 29 jul (paredes de 30 m numa arena de raio 60: 45 m de céu aberto, e os
      // campeões a 59 m em 3800 de 4000 passos). Desde a correção as paredes
      // vedam até 2×raio, por isso o que aqui se vê por cima é só o corte
      // visual. Diz-se, em vez de se deixar a imagem afirmar o contrário.
      const zMax = Math.max(...dados.quadros[est.quadro].map(a => Math.abs(a[2])));
      itens.sort((A, B) => A.d - B.d);
      for (const it of itens) {
        if (it.tipo === "poli") {
          ctx.beginPath();
          it.pts.forEach((q, i) => i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y));
          ctx.closePath();
          ctx.fillStyle = it.cor; ctx.fill();
          ctx.strokeStyle = "rgba(0,0,0,.35)"; ctx.lineWidth = 0.6; ctx.stroke();
        } else if (it.tipo === "circ") {
          ctx.beginPath(); ctx.arc(it.x, it.y, it.r, 0, 6.284);
          ctx.fillStyle = it.cor; ctx.fill();
        } else if (it.tipo === "ninho") {
          ctx.beginPath(); ctx.arc(it.x, it.y, it.r, 0, 6.284);
          ctx.fillStyle = "rgba(16,185,129,.22)"; ctx.fill();
          ctx.strokeStyle = COR.ninho; ctx.lineWidth = 2; ctx.stroke();
        } else {
          ctx.beginPath(); ctx.ellipse(it.sx, it.sy, it.r * 1.1, it.r * 0.45, 0, 0, 6.284);
          ctx.fillStyle = COR.sombra; ctx.fill();
          ctx.beginPath(); ctx.arc(it.x, it.y, it.r, 0, 6.284);
          ctx.fillStyle = it.cor; ctx.fill();
          ctx.strokeStyle = "rgba(255,255,255,.75)"; ctx.lineWidth = 1; ctx.stroke();
        }
      }
      if (zMax > ALTURA_VISUAL) {
        ctx.font = "12px system-ui, sans-serif";
        ctx.fillStyle = "#e8a33d";
        ctx.fillText(
          `altura maxima dos robos ${zMax.toFixed(1)} m — paredes desenhadas a `
          + `${ALTURA_VISUAL} m (vedam ate ${(2 * meta.raio_arena).toFixed(0)} m)`,
          10, h - 10);
      }
      if (aoMudar) {
        aoMudar({
          quadro: est.quadro, total: dados.quadros.length,
          passo: est.quadro * meta.passo,
          recolhas: dados.recolhas[est.quadro] || 0,
          alturaMax: zMax,
          aPassar: est.aPassar,
        });
      }
    }

    function tick(t) {
      if (est.aPassar && t - est.ultimo > 55 / est.velocidade) {
        est.quadro = (est.quadro + 1) % dados.quadros.length;
        est.ultimo = t;
        desenhar();
      }
      requestAnimationFrame(tick);
    }

    // Rodar com o rato, zoom com a roda: sem isto é uma imagem, não um
    // visualizador — e o ângulo certo para ver um beco não é o mesmo que para
    // ver quatro salas.
    let arrasta = false, ox = 0, oy = 0;
    canvas.addEventListener("mousedown", e => { arrasta = true; ox = e.clientX; oy = e.clientY; });
    window.addEventListener("mouseup", () => { arrasta = false; });
    window.addEventListener("mousemove", e => {
      if (!arrasta) return;
      est.az += (e.clientX - ox) * 0.008;
      est.el = Math.max(0.12, Math.min(1.45, est.el + (e.clientY - oy) * 0.006));
      ox = e.clientX; oy = e.clientY;
      desenhar();
    });
    canvas.addEventListener("wheel", e => {
      e.preventDefault();
      est.zoom = Math.max(0.4, Math.min(4, est.zoom * (e.deltaY > 0 ? 0.9 : 1.1)));
      desenhar();
    }, { passive: false });
    window.addEventListener("resize", desenhar);

    desenhar();
    requestAnimationFrame(tick);
    return {
      play: () => { est.aPassar = true; },
      pausa: () => { est.aPassar = false; desenhar(); },
      alterna: () => { est.aPassar = !est.aPassar; desenhar(); },
      velocidade: v => { est.velocidade = v; },
      irPara: q => { est.quadro = Math.max(0, Math.min(dados.quadros.length - 1, q | 0)); desenhar(); },
      vista: (az, el) => { est.az = az; est.el = el; desenhar(); },
    };
  }

  // Arranque SEM o servidor. O `ui.run_javascript` do NiceGUI só funciona depois
  // de o cliente estar ligado, e um `ui.timer(..., once=True)` criado durante a
  // construção da vista dispara antes disso — a primeira carga falhava em
  // silêncio e ficava um canvas preto. Aqui o canvas traz o episódio inicial
  // no `data-ep` e o próprio JS trata de arrancar quando estiver pronto.
  function tentarArrancar() {
    const c = document.querySelector("canvas[data-ep]");
    if (!c || !window.viz3d) return false;
    const alvo = c.getAttribute("data-ep");
    if (c.getAttribute("data-carregado") === alvo) return true;
    c.setAttribute("data-carregado", alvo);
    window.viz3d.carregar(c.id, alvo, function (e) {
      const el = document.getElementById("viz3d_estado");
      if (el) {
        el.textContent = "passo " + e.passo + " · quadro " + (e.quadro + 1) +
                         "/" + e.total + " · " + e.recolhas + " recolhas";
      }
    });
    return true;
  }

  // O NiceGUI só MONTA o conteúdo de um separador quando ele é aberto — o canvas
  // não existe no DOM até lá. Um polling com prazo desistia antes disso (o
  // separador pode ser aberto ao fim de meia hora), e o utilizador via um canvas
  // preto. O observador espera o tempo que for preciso e não custa nada.
  function autoArranque() {
    // O <script> está no HEAD: quando corre, `document.body` ainda pode ser null
    // e o `observe(null)` lança — matando o arranque em silêncio. Espera-se pelo
    // DOM antes de observar seja o que for.
    if (!document.body) {
      document.addEventListener("DOMContentLoaded", autoArranque, { once: true });
      return;
    }
    if (tentarArrancar()) return;
    const obs = new MutationObserver(function () {
      if (tentarArrancar()) obs.disconnect();
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

  window.viz3d = {
    autoArranque: autoArranque,
    carregar: async function (idCanvas, url, aoMudar) {
      const canvas = document.getElementById(idCanvas);
      if (!canvas) return null;
      const r = await fetch(url);
      if (!r.ok) throw new Error("episódio não encontrado: " + url);
      const dados = await r.json();
      if (window._viz3dAtual && window._viz3dAtual.pausa) window._viz3dAtual.pausa();
      window._viz3dAtual = criar(canvas, dados, aoMudar);
      return window._viz3dAtual;
    },
  };

  autoArranque();
})();
