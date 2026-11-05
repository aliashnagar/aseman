const panelMenu = document.querySelector('#panel-menu');
const panelMenuToggle = document.querySelector('.panel-menu-toggle');
const panelAside = panelMenu?.closest('aside');

panelMenuToggle?.addEventListener('click', () => {
  const isOpen = panelAside.classList.toggle('menu-open');
  panelMenuToggle.setAttribute('aria-expanded', String(isOpen));
});

panelMenu?.addEventListener('click', event => {
  if (!event.target.closest('a')) return;
  panelAside.classList.remove('menu-open');
  panelMenuToggle.setAttribute('aria-expanded', 'false');
});

document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || !panelAside?.classList.contains('menu-open')) return;
  panelAside.classList.remove('menu-open');
  panelMenuToggle.setAttribute('aria-expanded', 'false');
  panelMenuToggle.focus();
});
