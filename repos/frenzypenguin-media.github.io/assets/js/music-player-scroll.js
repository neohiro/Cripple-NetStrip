// Auto-fold music HUD when scrolling past 2x hero height
(function() {
  const player = document.getElementById('ul-player');
  if (!player) return;

  function checkScroll() {
    const hero = document.querySelector('.hero, .mhero, header, .site-header');
    const heroHeight = hero ? hero.offsetHeight : 300;
    const threshold = heroHeight * 2;

    if (window.scrollY > threshold) {
      player.classList.add('collapsed');
      try { localStorage.setItem('neohiro_ecosystem_audio_collapsed', 'true'); } catch(e){}
    }
  }

  window.addEventListener('scroll', checkScroll, { passive: true });
})();
