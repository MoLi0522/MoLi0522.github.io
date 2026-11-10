'use strict';

// All content remains readable without JavaScript. These are enhancements only.
document.documentElement.classList.add('has-js');

const themeButton = document.querySelector('.theme-toggle');
function syncThemeButton() {
  const dark = document.documentElement.dataset.theme === 'dark';
  if (themeButton) {
    themeButton.setAttribute('aria-label', dark ? '切换浅色模式' : '切换深色模式');
    themeButton.setAttribute('aria-pressed', String(dark));
  }
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#17231e' : '#f6f5f0');
}
if (themeButton) {
  themeButton.hidden = false;
  syncThemeButton();
  themeButton.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('theme', theme); } catch (_) { /* blocked storage is fine */ }
    syncThemeButton();
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
    let saved = null;
    try { saved = localStorage.getItem('theme'); } catch (_) { return; }
    if (!saved) {
      document.documentElement.dataset.theme = event.matches ? 'dark' : 'light';
      syncThemeButton();
    }
  });
}

const menuButton = document.querySelector('.menu-toggle');
const nav = document.querySelector('.site-nav');
function closeMenu() {
  nav?.classList.remove('is-open');
  menuButton?.setAttribute('aria-expanded', 'false');
  menuButton?.setAttribute('aria-label', '展开导航');
}
if (menuButton && nav) {
  menuButton.hidden = false;
  menuButton.addEventListener('click', () => {
    const open = nav.classList.toggle('is-open');
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? '收起导航' : '展开导航');
  });
  nav.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && nav.classList.contains('is-open')) {
      closeMenu();
      menuButton.focus();
    }
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.site-header')) closeMenu();
  });
  matchMedia('(min-width: 601px)').addEventListener('change', closeMenu);
}

const dataElement = document.querySelector('#post-data');
const search = document.querySelector('#post-search');
if (dataElement && search) {
  const posts = JSON.parse(dataElement.textContent);
  const cards = Array.from(document.querySelectorAll('[data-post-slug]'));
  const chips = Array.from(document.querySelectorAll('[data-filter]'));
  const empty = document.querySelector('.search-empty');
  const count = document.querySelector('#result-count');
  const params = new URLSearchParams(location.search);
  let filter = params.get('tag') || '';
  if (!chips.some(chip => chip.dataset.filter === filter)) filter = '';
  search.value = params.get('q') || '';
  document.querySelector('.filter-list').hidden = false;
  document.querySelector('.search-box').hidden = false;

  function updateResults(updateUrl = true) {
    const query = search.value.trim().toLocaleLowerCase();
    let total = 0;
    for (const card of cards) {
      const post = posts.find(p => p.slug === card.dataset.postSlug);
      const matchesTag = !filter || post.tags.includes(filter);
      const haystack = [post.title, post.summary, post.text, ...post.tags].join(' ').toLocaleLowerCase();
      const matchesQuery = query.split(/\s+/).every(word => haystack.includes(word));
      card.hidden = !(matchesTag && matchesQuery);
      if (!card.hidden) total += 1;
    }
    chips.forEach(chip => {
      const selected = chip.dataset.filter === filter;
      chip.classList.toggle('active', selected);
      chip.setAttribute('aria-pressed', String(selected));
    });
    empty.hidden = total !== 0;
    count.textContent = (filter || query) ? `找到 ${total} 篇文章 / 共 ${posts.length} 篇` : `共 ${posts.length} 篇文章`;
    if (updateUrl) {
      const next = new URL(location.href);
      next.searchParams.delete('tag');
      next.searchParams.delete('q');
      if (filter) next.searchParams.set('tag', filter);
      if (query) next.searchParams.set('q', search.value.trim());
      try { history.replaceState(null, '', next); } catch (_) { /* file:// and sandboxed contexts */ }
    }
  }
  chips.forEach(chip => chip.addEventListener('click', () => {
    filter = chip.dataset.filter;
    updateResults();
  }));
  search.addEventListener('input', () => updateResults());
  document.querySelector('#reset-search')?.addEventListener('click', () => {
    filter = '';
    search.value = '';
    updateResults();
    search.focus();
  });
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !event.ctrlKey && !event.metaKey && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
      event.preventDefault();
      search.focus();
    }
    if (event.key === 'Escape' && document.activeElement === search) {
      search.value = '';
      updateResults();
    }
  });
  updateResults(false);
}

for (const block of document.querySelectorAll('.code-block')) {
  // Clipboard requires a secure context (GitHub Pages uses HTTPS).
  if (!navigator.clipboard?.writeText) continue;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'copy-code';
  button.textContent = '复制代码';
  button.setAttribute('aria-label', '复制这段代码');
  button.setAttribute('aria-live', 'polite');
  block.querySelector('.code-caption').append(button);
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(block.querySelector('pre code').textContent);
      button.textContent = '已复制';
    } catch (_) {
      button.textContent = '请手动选择复制';
    }
    window.setTimeout(() => { button.textContent = '复制代码'; }, 2000);
  });
}

const tocLinks = Array.from(document.querySelectorAll('.article-toc nav a'));
if (tocLinks.length && 'IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        tocLinks.forEach(link => link.classList.toggle('active', link.hash === `#${entry.target.id}`));
      }
    }
  }, { rootMargin: '-100px 0px -60% 0px', threshold: 0 });
  tocLinks.forEach(link => {
    const heading = document.getElementById(link.hash.slice(1));
    if (heading) observer.observe(heading);
  });
}

const backTop = document.querySelector('.back-top');
if (backTop) {
  let scheduled = false;
  const updateTop = () => { backTop.hidden = window.scrollY < 600; scheduled = false; };
  window.addEventListener('scroll', () => {
    if (!scheduled) { requestAnimationFrame(updateTop); scheduled = true; }
  }, { passive: true });
  backTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  });
  updateTop();
}
