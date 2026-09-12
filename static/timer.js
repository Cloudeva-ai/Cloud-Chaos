<script>
(() => {
  window.__cloudChaosTimer?.();
  let interval;
  const observer = new MutationObserver(bind);
  function stop() { clearInterval(interval); observer.disconnect(); }
  window.__cloudChaosTimer = stop;
  function bind() {
    const label = document.getElementById('cc-timer-num');
    const fill = document.getElementById('cc-timer-fill');
    if (!label || !fill) return;
    observer.disconnect();
    const initial = Number(label.dataset.remaining);
    const duration = Number(label.dataset.duration);
    const origin = performance.now();
    const deadline = label.dataset.deadline;
    function paint() {
      if (!label.isConnected || label.dataset.deadline !== deadline) { stop(); return; }
      const remaining = Math.max(0, initial - (performance.now() - origin));
      const seconds = Math.ceil(remaining / 1000);
      if (label.textContent !== String(seconds)) label.textContent = String(seconds);
      label.classList.toggle('danger', seconds <= 15);
      fill.style.width = Math.min(100, remaining / duration * 100) + '%';
      fill.style.background = seconds <= 15 ? 'var(--error)' : 'var(--mint)';
      if (!remaining) {
        document.querySelectorAll('[class*="st-key-question_"] button, .st-key-fab_submit button').forEach(b => b.disabled = true);
        clearInterval(interval);
      }
    }
    paint();
    interval = setInterval(paint, 100);
  }
  observer.observe(document.body, {childList:true, subtree:true});
  bind();
})();
</script>
