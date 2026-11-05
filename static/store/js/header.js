const searchForm = document.querySelector('.header-search');
const searchInput = searchForm?.querySelector('input[type="search"]');
const searchToggle = searchForm?.querySelector('.search-toggle');

function closeSearch() {
  if (!searchForm?.classList.contains('open')) return;
  searchForm.classList.remove('open');
  searchToggle.setAttribute('aria-expanded', 'false');
  searchToggle.setAttribute('aria-label', 'باز کردن جستجو');
}

searchToggle?.addEventListener('click', () => {
  const isOpen = searchForm.classList.toggle('open');
  searchToggle.setAttribute('aria-expanded', String(isOpen));
  searchToggle.setAttribute('aria-label', isOpen ? 'بستن جستجو' : 'باز کردن جستجو');
  if (isOpen) searchInput.focus();
});

document.addEventListener('click', event => {
  if (!searchForm?.contains(event.target)) closeSearch();
});

searchInput?.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  closeSearch();
  searchToggle.focus();
});
