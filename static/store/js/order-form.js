const rows = document.querySelector('#order-item-rows');
const formCount = document.querySelector('#id_items-TOTAL_FORMS');
const emptyTemplate = document.querySelector('#order-item-empty-form');
const products = JSON.parse(document.querySelector('#order-products-data').textContent);
const productsById = new Map(products.map(product => [String(product.id), product]));

function updateOrderRow(row, updatePrice = false) {
  const productSelect = row.querySelector('select[name$="-product"]');
  const variantSelect = row.querySelector('select[name$="-variant"]');
  const priceInput = row.querySelector('input[name$="-unit_price"]');
  const product = productsById.get(productSelect.value);
  const selectedVariant = variantSelect.value;
  const variants = product?.variants || [];

  variantSelect.replaceChildren(new Option('بدون سایز', ''));
  variants.forEach(variant => {
    variantSelect.add(new Option(variant.size, String(variant.id)));
  });
  if (variants.some(variant => String(variant.id) === selectedVariant)) {
    variantSelect.value = selectedVariant;
  } else if (variants.length) {
    variantSelect.value = String(variants[0].id);
  }

  if (updatePrice || !priceInput.value) {
    const variant = variants.find(item => String(item.id) === variantSelect.value);
    priceInput.value = variant ? variant.price : product?.price || '';
  }
}

rows.querySelectorAll('.order-item-row').forEach(row => updateOrderRow(row));

document.querySelector('#add-order-item').addEventListener('click', () => {
  const index = Number(formCount.value);
  rows.insertAdjacentHTML('beforeend', emptyTemplate.innerHTML.replaceAll('__prefix__', index));
  formCount.value = String(index + 1);
  updateOrderRow(rows.lastElementChild);
});

rows.addEventListener('change', event => {
  const row = event.target.closest('.order-item-row');
  if (!row) return;
  if (event.target.matches('select[name$="-product"]')) {
    row.querySelector('select[name$="-variant"]').value = '';
    updateOrderRow(row, true);
  }
  if (event.target.matches('select[name$="-variant"]')) updateOrderRow(row, true);
});

rows.addEventListener('click', event => {
  const removeButton = event.target.closest('[data-remove-order-item]');
  if (!removeButton) return;
  const row = removeButton.closest('.order-item-row');
  row.querySelector('input[name$="-DELETE"]').checked = true;
  row.hidden = true;
});
