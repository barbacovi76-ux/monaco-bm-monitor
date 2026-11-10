/**
 * Monaco Agency — Animated Background Engine v1.0
 * Particle grid + flowing lines + subtle glow
 * Elegante e performático — usa requestAnimationFrame
 */
(function() {
  'use strict';

  const cfg = {
    particles:    38,
    lineDistance: 140,
    speed:        0.28,
    particleSize: 1.4,
    color:        { r: 200, g: 164, b: 74 },   // gold
    colorSecond:  { r: 110, g: 142, b: 255 },   // blue accent
    bgGrid:       true,
    gridSize:     56,
  };

  let canvas, ctx, W, H, dpr, particles = [], rafId;
  let mouseX = -9999, mouseY = -9999;

  function init() {
    canvas = document.getElementById('mnc-canvas');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.id = 'mnc-canvas';
      canvas.style.cssText = 'position:fixed;inset:0;z-index:0;pointer-events:none';
      document.body.prepend(canvas);
    }
    ctx = canvas.getContext('2d');
    resize();
    spawnParticles();
    window.addEventListener('resize', debounce(resize, 160));
    document.addEventListener('mousemove', e => { mouseX = e.clientX; mouseY = e.clientY; });
    loop();
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    canvas.width  = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width  = W + 'px';
    canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);
  }

  function spawnParticles() {
    particles = [];
    for (let i = 0; i < cfg.particles; i++) {
      particles.push(mkParticle(true));
    }
  }

  function mkParticle(random) {
    const gold = Math.random() > .65;
    const c = gold ? cfg.color : cfg.colorSecond;
    return {
      x:    random ? Math.random() * W : (Math.random() < .5 ? -4 : W + 4),
      y:    random ? Math.random() * H : Math.random() * H,
      vx:   (Math.random() - .5) * cfg.speed * 2,
      vy:   (Math.random() - .5) * cfg.speed * 2,
      size: cfg.particleSize * (.6 + Math.random() * .8),
      alpha:Math.random() * .5 + .2,
      cr: c.r, cg: c.g, cb: c.b,
      pulse: Math.random() * Math.PI * 2,
    };
  }

  function loop() {
    rafId = requestAnimationFrame(loop);
    draw();
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);

    // --- subtle grid ---
    if (cfg.bgGrid) {
      ctx.strokeStyle = 'rgba(26,26,40,0.55)';
      ctx.lineWidth = .5;
      ctx.beginPath();
      for (let x = 0; x < W; x += cfg.gridSize) {
        ctx.moveTo(x, 0); ctx.lineTo(x, H);
      }
      for (let y = 0; y < H; y += cfg.gridSize) {
        ctx.moveTo(0, y); ctx.lineTo(W, y);
      }
      ctx.stroke();
    }

    // --- update + draw particles ---
    const now = Date.now() * .001;
    particles.forEach((p, i) => {
      p.x += p.vx; p.y += p.vy;
      p.pulse += .018;

      // Mouse repulsion (subtle)
      const dx = p.x - mouseX, dy = p.y - mouseY;
      const dist = Math.sqrt(dx*dx + dy*dy);
      if (dist < 90) {
        p.vx += (dx / dist) * .08;
        p.vy += (dy / dist) * .08;
      }

      // Clamp speed
      const spd = Math.sqrt(p.vx*p.vx + p.vy*p.vy);
      if (spd > cfg.speed * 2.5) { p.vx *= .92; p.vy *= .92; }

      // Wrap around edges
      if (p.x < -6) p.x = W + 4;
      if (p.x > W + 6) p.x = -4;
      if (p.y < -6) p.y = H + 4;
      if (p.y > H + 6) p.y = -4;

      const pAlpha = p.alpha * (.75 + .25 * Math.sin(p.pulse));

      // Dot glow
      const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size * 4);
      grad.addColorStop(0, `rgba(${p.cr},${p.cg},${p.cb},${pAlpha})`);
      grad.addColorStop(1, 'transparent');
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * 4, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();

      // Dot core
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${p.cr},${p.cg},${p.cb},${pAlpha * 1.5})`;
      ctx.fill();
    });

    // --- connection lines ---
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i], b = particles[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const d = Math.sqrt(dx*dx + dy*dy);
        if (d < cfg.lineDistance) {
          const lineAlpha = (1 - d / cfg.lineDistance) * .22;
          // Blend colors
          const r = Math.round((a.cr + b.cr) / 2);
          const g = Math.round((a.cg + b.cg) / 2);
          const bl = Math.round((a.cb + b.cb) / 2);
          ctx.beginPath();
          ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(${r},${g},${bl},${lineAlpha})`;
          ctx.lineWidth = .6;
          ctx.stroke();
        }
      }
    }

    // --- top-right radial glow ---
    const glowGrad = ctx.createRadialGradient(W, 0, 0, W, 0, W * .55);
    glowGrad.addColorStop(0, `rgba(200,164,74,0.06)`);
    glowGrad.addColorStop(1, 'transparent');
    ctx.fillStyle = glowGrad;
    ctx.fillRect(0, 0, W, H);
  }

  function debounce(fn, ms) {
    let t;
    return function() { clearTimeout(t); t = setTimeout(() => fn.apply(this, arguments), ms); };
  }

  // Boot
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Ripple on buttons
  document.addEventListener('click', function(e) {
    const btn = e.target.closest('.btn, .nav-btn, .psw-btn');
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 1.6;
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top - size / 2;
    const ripple = document.createElement('span');
    ripple.className = 'btn-ripple';
    ripple.style.cssText = `width:${size}px;height:${size}px;left:${x}px;top:${y}px`;
    btn.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
  }, true);

  // Ripple cursor position for radial highlight
  document.addEventListener('mousemove', function(e) {
    const btn = e.target.closest('.btn, .nav-btn');
    if (!btn) return;
    const r = btn.getBoundingClientRect();
    btn.style.setProperty('--rx', ((e.clientX - r.left) / r.width * 100) + '%');
    btn.style.setProperty('--ry', ((e.clientY - r.top)  / r.height * 100) + '%');
  });

})();
