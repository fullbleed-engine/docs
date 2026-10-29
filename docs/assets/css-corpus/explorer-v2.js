(() => {
  'use strict';
  const root = document.getElementById('css-explorer');
  if (!root) return;
  // Old fixture links used the theme's global-search parameter. Migrate it
  // before the theme starts so a shared mobile link leaves the PDF accessible.
  const initialUrl = new URL(location.href);
  if (initialUrl.searchParams.has('q')) {
    if (!initialUrl.searchParams.has('query')) initialUrl.searchParams.set('query', initialUrl.searchParams.get('q'));
    initialUrl.searchParams.delete('q');
    history.replaceState(null, '', initialUrl);
  }
  const find = (id) => document.getElementById(`ce-${id}`);
  const create = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const versionsUrl = new URL(root.dataset.versions, location.href);
  let indexUrl;
  const perPage = 12;
  const verdicts = ['PASS', 'FAIL', 'REFERENCE-DISPUTED'];
  let data, fixtures, selected, pageNumber = 0;
  const badge = (status) => {
    const element = create('span', status, 'ce-verdict');
    element.dataset.verdict = status;
    return element;
  };
  const assetUrl = (path) => {
    if (!/^(?:pdfs|refs|out)\/[a-z0-9_-]+\/[a-z0-9_.-]+\.(?:pdf|png)$/.test(path)) throw new Error('Invalid evidence path');
    return new URL(path, indexUrl).href;
  };
  const link = (title, href, download = false) => {
    const element = create('a', title);
    element.href = href;
    if (download) element.download = '';
    return element;
  };
  const saveUrl = (push = false) => {
    const url = new URL(location.href);
    for (const [key, value] of [['version', data.version], ['query', find('search').value], ['category', find('category').value],
      ['verdict', find('verdict').value], ['case', selected || '']]) {
      if (value) url.searchParams.set(key, value); else url.searchParams.delete(key);
    }
    history[push ? 'pushState' : 'replaceState'](null, '', url);
  };
  function showDetail(key, focus = false) {
    const detail = find('detail');
    detail.replaceChildren();
    const fixture = fixtures.get(key);
    if (!fixture) { detail.hidden = true; selected = null; return; }
    selected = key;
    detail.hidden = false;
    const title = create('h2', fixture.id);
    title.id = 'ce-detail-title';
    detail.append(title, badge(fixture.status), create('p', 'Upstream fixture: ' + fixture.description));
    const difference = Number(fixture.differencePercent).toFixed(4);
    detail.append(create('p', `${fixture.category} · ${fixture.feature} · Above-floor page difference: ${difference}%`));
    detail.append(create('p', `Reference renderer: ${fixture.referenceRenderer}. Reference metadata: ${fixture.referenceStatus}.`));
    if (fixture.diagnosis) detail.append(create('p', `Comparator diagnosis: ${fixture.diagnosis}`));
    const links = create('p', undefined, 'ce-links');
    links.append(link('Download Fullbleed PDF', assetUrl(fixture.pdf), true), link('View HTML/CSS fixture', fixture.sourceUrl));
    const share = link('Link to this case', location.href);
    const shareUrl = new URL(location.href);
    shareUrl.searchParams.set('case', key);
    share.href = shareUrl.href;
    links.append(share);
    detail.append(links);
    if (fixture.referenceNote) {
      const note = create('details');
      note.append(create('summary', 'Upstream reference review note'), create('p', fixture.referenceNote));
      detail.append(note);
    }
    const digest = create('details');
    digest.append(create('summary', 'PDF checksum'), create('p', `SHA-256: ${fixture.pdfSha256}`));
    detail.append(digest);
    fixture.pages.forEach((page, index) => {
      detail.append(create('h3', `Page ${index + 1}`));
      const images = create('div', undefined, 'ce-images');
      for (const [key, label] of [['reference', `${fixture.referenceRenderer} reference`], ['candidate', `Fullbleed ${data.version}`]]) {
        const figure = create('figure');
        figure.append(create('figcaption', label));
        if (page[key]) {
          const url = assetUrl(page[key]);
          const anchor = link('', url);
          anchor.setAttribute('aria-label', `Open full-size ${label}, page ${index + 1}`);
          const image = document.createElement('img');
          image.src = url;
          image.alt = `${label}, ${fixture.id}, page ${index + 1}`;
          image.loading = 'lazy';
          image.addEventListener('error', () => { image.replaceWith(create('p', 'This preview could not load. Use the PDF or complete report.')); });
          anchor.append(image);
          figure.append(anchor);
        } else figure.append(create('p', 'No page on this side of the comparison.'));
        images.append(figure);
      }
      detail.append(images);
    });
    if (focus) { detail.focus({preventScroll: true}); detail.scrollIntoView({block: 'start', behavior: 'auto'}); }
  }
  function renderResults() {
    const query = find('search').value.trim().toLowerCase();
    const category = find('category').value;
    const verdict = find('verdict').value;
    const filtered = data.fixtures.filter((f) => (!category || f.category === category) && (!verdict || f.status === verdict)
      && `${f.key} ${f.feature} ${f.description}`.toLowerCase().includes(query));
    const pages = Math.max(1, Math.ceil(filtered.length / perPage));
    pageNumber = Math.min(pageNumber, pages - 1);
    const start = pageNumber * perPage;
    find('results-status').textContent = filtered.length ? `${filtered.length.toLocaleString()} matching fixtures. Showing ${start + 1}–${Math.min(start + perPage, filtered.length)}.` : 'No fixtures match these filters. Try a broader term or another verdict.';
    const results = find('results');
    results.replaceChildren();
    for (const fixture of filtered.slice(start, start + perPage)) {
      const article = create('article', undefined, 'ce-result');
      const button = create('button', fixture.id);
      button.type = 'button';
      button.setAttribute('aria-label', `Inspect ${fixture.id}`);
      button.addEventListener('click', () => { selected = fixture.key; saveUrl(true); showDetail(fixture.key, true); });
      const metadata = create('p', undefined, 'ce-meta');
      metadata.append(badge(fixture.status), create('span', fixture.category), create('span', `${fixture.pages.length} page${fixture.pages.length === 1 ? '' : 's'}`));
      article.append(button, metadata, create('p', 'Upstream fixture: ' + fixture.description));
      results.append(article);
    }
    find('previous').disabled = pageNumber === 0;
    find('next').disabled = pageNumber >= pages - 1;
    find('page').textContent = `Page ${pageNumber + 1} of ${pages}`;
  }
  function restoreUrl() {
    const params = new URL(location.href).searchParams;
    if (params.get('version') !== data.version) { location.reload(); return; }
    find('search').value = params.get('query') || '';
    find('category').value = params.get('category') || '';
    find('verdict').value = params.get('verdict') || '';
    if (find('category').selectedIndex < 0) find('category').value = '';
    if (find('verdict').selectedIndex < 0) find('verdict').value = '';
    pageNumber = 0;
    renderResults();
    showDetail(params.get('case'));
  }
  async function start() {
    const versionsResponse = await fetch(versionsUrl);
    if (!versionsResponse.ok) throw new Error('Package versions unavailable');
    const versions = await versionsResponse.json();
    if (versions.schema !== 'fullbleed.css-explorer-versions.v1' || !Array.isArray(versions.versions)
      || !versions.versions.length || versions.versions.some(v => typeof v !== 'string' || !/^\d+\.\d+\.\d+$/.test(v))
      || new Set(versions.versions).size !== versions.versions.length || !versions.versions.includes(versions.current)) {
      throw new Error('Invalid package version inventory');
    }
    const requested = new URL(location.href).searchParams.get('version');
    const version = versions.versions.includes(requested) ? requested : versions.current;
    indexUrl = new URL(`${version}/index.json`, versionsUrl);
    for (const value of versions.versions) {
      const option = create('option', `${value}${value === versions.current ? ' (current)' : ' (historical)'}`);
      option.value = value;
      find('version').append(option);
    }
    find('version').value = version;
    const response = await fetch(indexUrl);
    if (!response.ok) throw new Error('Fixture index unavailable');
    data = await response.json();
    if (data.schema !== 'fullbleed.css-explorer.v1' || data.packageSource !== 'published' || data.version !== version
      || !Array.isArray(data.fixtures) || data.fixtures.length !== data.total) throw new Error('Invalid fixture index');
    fixtures = new Map(data.fixtures.map((f) => [f.key, f]));
    if (fixtures.size !== data.total || data.fixtures.some((f) => !verdicts.includes(f.status))) throw new Error('Invalid verdict inventory');
    for (const status of verdicts) {
      const count = data.fixtures.filter((f) => f.status === status).length;
      if (data.counts[status] !== count) throw new Error('Inconsistent verdict counts');
      const span = create('span');
      span.append(badge(status), document.createTextNode(` ${count.toLocaleString()}`));
      find('counts').append(span);
    }
    for (const category of [...new Set(data.fixtures.map((f) => f.category))].sort()) {
      const option = create('option', category);
      option.value = category;
      find('category').append(option);
    }
    find('provenance').append(link('Complete evidence ZIP', data.archiveUrl),
      link('Raw comparison JSON', new URL('report.json', indexUrl).href),
      link('Run and wheel record', new URL('fullbleed-run.json', indexUrl).href));
    const changeFilter = () => { pageNumber = 0; selected = null; saveUrl(); showDetail(null); renderResults(); };
    find('search').addEventListener('input', changeFilter);
    find('category').addEventListener('change', changeFilter);
    find('verdict').addEventListener('change', changeFilter);
    find('version').addEventListener('change', () => {
      const url = new URL(location.href);
      url.searchParams.set('version', find('version').value);
      location.assign(url.href);
    });
    for (const [name, direction] of [['previous', -1], ['next', 1]]) find(name).addEventListener('click', () => {
      pageNumber += direction; renderResults(); find('results-status').scrollIntoView({block: 'center'});
    });
    addEventListener('popstate', restoreUrl);
    find('loading').textContent = `${data.total.toLocaleString()} fixtures · published Fullbleed ${data.version} · full comparison gate ${data.gatePassed ? 'passed' : 'failed'}`;
    find('controls').hidden = false;
    const normalized = new URL(location.href);
    normalized.searchParams.set('version', data.version);
    history.replaceState(null, '', normalized);
    restoreUrl();
    saveUrl();
  }
  start().catch(() => {
    find('loading').textContent = 'The fixture browser could not load. Follow the evidence guide link above to download the complete report.';
    find('loading').classList.add('ce-error');
    find('controls').hidden = true;
  });
})();
