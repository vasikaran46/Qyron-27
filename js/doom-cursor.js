// ============================================================
// DOCTOR DOOM QUANTUM RETICLE CURSOR WITH GOLDEN DOOM MASK
// ============================================================
(() => {
  // Only activate on devices with a mouse/pointer
  if (window.matchMedia('(hover: none) and (pointer: coarse)').matches) return;

  const dot = document.createElement('div');
  dot.className = 'doom-cursor-dot';

  const ring = document.createElement('div');
  ring.className = 'doom-cursor-ring';
  ring.innerHTML = `
    <span class="hud-tick tick-top"></span>
    <span class="hud-tick tick-right"></span>
    <span class="hud-tick tick-bottom"></span>
    <span class="hud-tick tick-left"></span>
    <div class="cursor-gold-logo">
      <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2 L4 8 L6 10 L12 5 L18 10 L20 8 Z" fill="#0a3a22" stroke="#e5c17c" stroke-width="1.2"/>
        <path d="M6 9 L18 9 L17 19 L12 22 L7 19 Z" fill="#18231d" stroke="#e5c17c" stroke-width="1.2"/>
        <line x1="8" y1="12" x2="11" y2="12" stroke="#3ddc84" stroke-width="1.5"/>
        <line x1="13" y1="12" x2="16" y2="12" stroke="#3ddc84" stroke-width="1.5"/>
        <line x1="10" y1="17" x2="10" y2="19" stroke="#e5c17c" stroke-width="1"/>
        <line x1="12" y1="17" x2="12" y2="20" stroke="#e5c17c" stroke-width="1"/>
        <line x1="14" y1="17" x2="14" y2="19" stroke="#e5c17c" stroke-width="1"/>
      </svg>
    </div>
  `;

  document.body.appendChild(dot);
  document.body.appendChild(ring);

  let mouseX = -100, mouseY = -100;
  let ringX = -100, ringY = -100;
  let isHovered = false;

  window.addEventListener('mousemove', e => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    dot.style.transform = `translate3d(${mouseX}px, ${mouseY}px, 0)`;
  }, { passive: true });

  // Smooth lerp animation for outer reticle
  function render() {
    ringX += (mouseX - ringX) * 0.22;
    ringY += (mouseY - ringY) * 0.22;
    ring.style.transform = `translate3d(${ringX}px, ${ringY}px, 0) ${isHovered ? 'scale(1.45)' : 'scale(1)'}`;
    requestAnimationFrame(render);
  }
  requestAnimationFrame(render);

  // Hover detection for interactive elements
  const hoverSelectors = 'a, button, input, select, textarea, label, [data-egg], [data-open], .singularity-core, .faq-trigger, .stat-item, .quote-grid blockquote, .btn-register';
  document.addEventListener('mouseover', e => {
    if (e.target.closest(hoverSelectors)) {
      isHovered = true;
      ring.classList.add('is-hovered');
      dot.classList.add('is-hovered');
    }
  });

  document.addEventListener('mouseout', e => {
    if (e.target.closest(hoverSelectors)) {
      isHovered = false;
      ring.classList.remove('is-hovered');
      dot.classList.remove('is-hovered');
    }
  });

  // Click burst animation
  window.addEventListener('mousedown', () => {
    ring.classList.add('is-clicking');
  });
  window.addEventListener('mouseup', () => {
    ring.classList.remove('is-clicking');
  });
})();
