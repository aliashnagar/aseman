const socialRows = document.querySelector('#footer-social-rows');
const socialCount = document.querySelector('#id_footer_socials-TOTAL_FORMS');
const socialMax = document.querySelector('#id_footer_socials-MAX_NUM_FORMS');
const socialTemplate = document.querySelector('#footer-social-empty-form');
const addSocialButton = document.querySelector('#add-footer-social');

if (socialRows && socialCount && socialTemplate && addSocialButton) {
  const updateAddButton = () => {
    addSocialButton.disabled = Number(socialCount.value) >= Number(socialMax?.value || 20);
  };

  addSocialButton.addEventListener('click', () => {
    const index = Number(socialCount.value);
    const markup = socialTemplate.innerHTML.replaceAll('__prefix__', index);
    socialRows.insertAdjacentHTML('beforeend', markup);
    socialCount.value = String(index + 1);
    updateAddButton();
    socialRows.lastElementChild.querySelector('input:not([type="hidden"]), select')?.focus();
  });

  socialRows.addEventListener('click', event => {
    const removeButton = event.target.closest('[data-remove-footer-social]');
    if (!removeButton) return;
    const row = removeButton.closest('.social-link-row');
    const deleteInput = row.querySelector('input[name$="-DELETE"]');
    if (deleteInput) deleteInput.checked = true;
    row.hidden = true;
  });

  updateAddButton();
}
