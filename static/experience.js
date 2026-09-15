<script>
(() => {
  if (window.__cloudChaosExperience) return;
  window.__cloudChaosExperience = true;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let paused = reduced.matches;
  try { paused = reduced.matches || localStorage.getItem('cloud-chaos-motion') === 'paused'; } catch (_) {}
  function apply() {
    document.documentElement.classList.toggle('motion-paused', paused);
    document.querySelectorAll('.motion-toggle').forEach(button => {
      const label = paused ? 'Play animations' : 'Pause animations';
      if (button.getAttribute('aria-label') !== label) {
        button.setAttribute('aria-label', label);
        button.title = label;
        button.querySelector('span').textContent = paused ? 'play_arrow' : 'pause';
      }
    });
    document.querySelectorAll('video').forEach(video => {
      if (paused) video.pause();
      else if (video.paused) video.play().catch(() => {});
    });
    document.querySelectorAll('img.mascot-animation').forEach(image => {
      if (!image.dataset.animationSrc) image.dataset.animationSrc = image.currentSrc || image.src;
      image.src = paused ? 'app/static/mascot-idle.png' : image.dataset.animationSrc;
    });
  }
  document.addEventListener('click', event => {
    if (!event.target.closest('.motion-toggle')) return;
    paused = !paused;
    try { localStorage.setItem('cloud-chaos-motion', paused ? 'paused' : 'playing'); } catch (_) {}
    apply();
  });
  reduced.addEventListener('change', event => { paused = event.matches; apply(); });
  new MutationObserver(apply).observe(document.body, {childList:true, subtree:true});
  apply();
})();
</script>
