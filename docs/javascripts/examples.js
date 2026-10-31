/* The catalog remains a complete, linked document when scripting is unavailable. */
(() => {
  const catalog = document.getElementById('example-catalog');
  const controls = document.querySelector('.example-filters');
  const status = document.querySelector('.example-count');
  if (!catalog || !controls || !status) return;

  const cards = [...catalog.querySelectorAll('.example-card')];
  const buttons = [...controls.querySelectorAll('[data-example-filter]')];
  const types = new Set(buttons.map(button => button.dataset.exampleFilter));
  if (!cards.length || !types.has('all')) return;

  function linkedCard() {
    try {
      return document.getElementById(decodeURIComponent(location.hash.slice(1)))
        ?.closest('.example-card');
    } catch {
      return null;
    }
  }

  function apply(type, historyMode) {
    type = types.has(type) ? type : 'all';
    let count = 0;
    for (const card of cards) {
      card.hidden = type !== 'all' && card.dataset.exampleKind !== type;
      if (!card.hidden) count += 1;
    }
    for (const button of buttons) {
      button.setAttribute('aria-pressed', String(button.dataset.exampleFilter === type));
    }
    status.textContent = `Showing ${count} of ${cards.length} examples`;
    if (historyMode) {
      const url = new URL(location.href);
      if (type === 'all') url.searchParams.delete('type');
      else url.searchParams.set('type', type);
      if (linkedCard()?.hidden) url.hash = '';
      if (url.href !== location.href) history[historyMode + 'State'](null, '', url);
    }
  }

  function followLocation() {
    const type = new URL(location.href).searchParams.get('type') || 'all';
    const target = linkedCard();
    // A shared example anchor takes precedence over a conflicting category.
    if (target && types.has(type) && type !== 'all' && target.dataset.exampleKind !== type) {
      apply('all', 'replace');
      requestAnimationFrame(() => target.querySelector('h2').scrollIntoView());
    } else {
      apply(type);
    }
  }

  for (const button of buttons) {
    button.addEventListener('click', () => apply(button.dataset.exampleFilter, 'push'));
  }
  addEventListener('popstate', followLocation);
  addEventListener('hashchange', followLocation);
  followLocation();
  controls.hidden = false;
})();
