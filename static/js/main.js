// Copy to clipboard — event delegation so hidden/dynamic panels work reliably
document.addEventListener('click', function (e) {
  const btn = e.target.closest('[data-copy]');
  if (!btn) return;

  const text = btn.dataset.copy;
  if (!text) return;

  const orig = btn.innerHTML;
  const succeed = () => {
    btn.innerHTML = '✓ Copied';
    btn.classList.add('text-teal-400', '!border-teal-500/40');
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.classList.remove('text-teal-400', '!border-teal-500/40');
    }, 2000);
  };

  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(succeed).catch(() => fallback(text, succeed));
  } else {
    fallback(text, succeed);
  }
});

function fallback(text, succeed) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
    succeed();
  } catch (_) {}
  document.body.removeChild(ta);
}
