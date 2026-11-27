(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const toast = msg => {
    const t = $('#toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toast.id);
    toast.id = setTimeout(() => t.classList.remove('show'), 3600);
  };

  // Boot lines on the loading screen
  const lines = [
    'INITIALIZING QUANTUM HACKATHON ENVIRONMENT',
    'LOADING MATHEMATICAL ALGORITHM MODULES',
    'PREPARING CIRCUIT SIMULATION INTERFACE',
    'CONNECTING TO PARTICIPANT REGISTRY',
    'SYSTEM READY — WELCOME TO QYRON 27'
  ];
  const boot = $('#bootLine');
  let i = 0;
  if (boot) {
    const id = setInterval(() => {
      boot.textContent = lines[++i % lines.length];
      if (!document.body.contains(boot)) clearInterval(id);
    }, 330);
  }

  // Hover / focus / tap notes
  const tip = document.createElement('div');
  tip.className = 'egg-tip';
  document.body.appendChild(tip);
  const place = e => {
    tip.style.left = Math.min(e.clientX + 16, innerWidth - 340) + 'px';
    tip.style.top = (e.clientY + 18) + 'px';
  };
  document.addEventListener('mouseover', e => {
    const el = e.target.closest('[data-egg]');
    if (!el) return;
    tip.textContent = el.dataset.egg;
    tip.classList.add('on');
    place(e);
  });
  document.addEventListener('mousemove', e => tip.classList.contains('on') && place(e));
  document.addEventListener('mouseout', e => {
    if (e.target.closest('[data-egg]')) tip.classList.remove('on');
  });
  document.addEventListener('click', e => {
    const el = e.target.closest('[data-egg]');
    if (el && matchMedia('(hover:none)').matches) toast(el.dataset.egg);
  });

  // Click the Doctor Doom Mask Core: Superposition cycles & Entangled particles
  const core = $('#qCore');
  let clicks = 0;
  if (core) {
    core.addEventListener('click', () => {
      clicks++;
      core.classList.remove('qcore-flip');
      void core.offsetWidth;
      core.classList.add('qcore-flip');
      const states = ['|0⟩ GROUND STATE', '|1⟩ EXCITED STATE', '|+⟩ QUANTUM SUPERPOSITION'];
      if (clicks < 3) {
        toast(`[STATE ${clicks}]: ${states[clicks % 3]} — Coherence maintained.`);
      } else {
        clicks = 0;
        toast('WAVEFUNCTION MEASURED: Entangled quantum state observed!');
        const r = core.getBoundingClientRect();
        const mk = dx => {
          const d = document.createElement('i');
          d.className = 'entangled';
          d.style.left = r.left + r.width / 2 + 'px';
          d.style.top = r.top + r.height / 2 + 'px';
          document.body.appendChild(d);
          requestAnimationFrame(() => {
            d.style.transform = `translate(${dx}px,${-dx / 3}px)`;
            d.style.opacity = '0';
          });
          setTimeout(() => d.remove(), 1500);
        };
        mk(-240);
        mk(240);
      }
    });
  }

  // Konami code: Quantum Realm mode
  const seq = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
  let pos = 0;
  addEventListener('keydown', e => {
    pos = (e.key === seq[pos] || e.key.toLowerCase() === seq[pos]) ? pos + 1 : 0;
    if (pos === seq.length) {
      pos = 0;
      const on = document.body.classList.toggle('quantum-realm');
      toast(on
        ? 'QUANTUM COHERENCE MODE ACTIVATED'
        : 'STANDARD MODE RESTORED');
    }
  });

  // Console easter egg
  console.log('%cWELCOME TO QYRON 27.', 'color:#3ddc84;font:700 20px monospace;text-shadow:0 0 8px #3ddc84');
  console.log('%cDepartment of Mathematics — Patrician College of Arts and Science', 'color:#e5c17c;font:13px monospace');
})();
