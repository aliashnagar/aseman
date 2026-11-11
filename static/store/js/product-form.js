const imageInput = document.querySelector('#id_image');
const preview = document.querySelector('#image-preview');
const additionalImagesInput = document.querySelector('#id_additional_images');
const galleryPreview = document.querySelector('#gallery-preview');
const discountToggle = document.querySelector('#id_discount_enabled');
const discountPercent = document.querySelector('#id_discount_percent');
const variantRows = document.querySelector('#variant-rows');
const variantCount = document.querySelector('#id_variants-TOTAL_FORMS');
const emptyVariantTemplate = document.querySelector('#variant-empty-form');

imageInput?.addEventListener('change', () => {
  const file = imageInput.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.addEventListener('load', () => {
    const image = new Image();
    image.alt = 'پیش‌نمایش تصویر محصول';
    image.src = reader.result;
    preview.replaceChildren(image);
    preview.hidden = false;
  });
  reader.readAsDataURL(file);
});

additionalImagesInput?.addEventListener('change', () => {
  galleryPreview.replaceChildren();
  Array.from(additionalImagesInput.files || []).forEach(file => {
    const reader = new FileReader();
    reader.addEventListener('load', () => {
      const image = new Image();
      image.alt = `پیش‌نمایش ${file.name}`;
      image.src = reader.result;
      galleryPreview.append(image);
    });
    reader.readAsDataURL(file);
  });
});

discountToggle?.addEventListener('change', () => {
  discountPercent.disabled = !discountToggle.checked;
  if (!discountToggle.checked) discountPercent.value = '';
});

if (discountToggle && discountPercent) {
  discountPercent.disabled = !discountToggle.checked;
}

document.querySelector('#add-variant')?.addEventListener('click', () => {
  const index = Number(variantCount.value);
  const html = emptyVariantTemplate.innerHTML.replaceAll('__prefix__', index);
  variantRows.insertAdjacentHTML('beforeend', html);
  variantCount.value = String(index + 1);
});

variantRows?.addEventListener('click', event => {
  const removeButton = event.target.closest('[data-remove-variant]');
  if (!removeButton) return;
  const row = removeButton.closest('.variant-row');
  row.querySelector('[name$="-DELETE"]').checked = true;
  row.hidden = true;
});

document.querySelector('[name="clear_image"]')?.addEventListener('change', event => {
  if (event.target.checked) {
    preview.replaceChildren();
    preview.hidden = true;
    imageInput.value = '';
  }
});
