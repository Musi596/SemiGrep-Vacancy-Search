const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (!reduceMotion) {
  const revealObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach(element => revealObserver.observe(element));

  document.querySelectorAll('[data-tilt]').forEach(card => {
    card.addEventListener('pointermove', event => {
      const bounds = card.getBoundingClientRect();
      const x = event.clientX - bounds.left;
      const y = event.clientY - bounds.top;
      card.style.setProperty('--px', `${x}px`);
      card.style.setProperty('--py', `${y}px`);
      card.style.transform = `rotateX(${(0.5 - y / bounds.height) * 5}deg) rotateY(${(x / bounds.width - 0.5) * 5}deg)`;
    });
    card.addEventListener('pointerleave', () => { card.style.transform = ''; });
  });

  const art = document.querySelector('.hero-art');
  art?.addEventListener('pointermove', event => {
    const bounds = art.getBoundingClientRect();
    art.style.setProperty('--mx', `${((event.clientX - bounds.left) / bounds.width - 0.5) * 12}deg`);
    art.style.setProperty('--my', `${((event.clientY - bounds.top) / bounds.height - 0.5) * -12}deg`);
  });
  art?.addEventListener('pointerleave', () => {
    art.style.setProperty('--mx', '0deg');
    art.style.setProperty('--my', '0deg');
  });
}
