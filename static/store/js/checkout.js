const form = document.querySelector('#checkout-form');
const itemList = document.querySelector('#checkout-items');
const totalElement = document.querySelector('#checkout-total');
const submitButton = document.querySelector('#checkout-submit');
const messageElement = document.querySelector('#checkout-message');
const fa = value => Number(value || 0).toLocaleString('fa-IR');
const money = value => `${fa(value)} تومان`;
const normalizeDigits = value => value
  .replace(/[۰-۹]/g, digit => String(digit.charCodeAt(0) - 1776))
  .replace(/[٠-٩]/g, digit => String(digit.charCodeAt(0) - 1632));
const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[char]));

let products = [];
let cart = {};
try {
  const savedCart = JSON.parse(localStorage.getItem('as_cart') || '{}');
  if (savedCart && !Array.isArray(savedCart) && typeof savedCart === 'object') {
    cart = Object.fromEntries(Object.entries(savedCart)
      .map(([key, quantity]) => [key, Number(quantity)])
      .filter(([, quantity]) => Number.isInteger(quantity) && quantity > 0));
  }
} catch (error) {
  console.error('Could not read the shopping cart from browser storage.', error);
}

function getItems() {
  return Object.entries(cart).flatMap(([key, quantity]) => {
    const [productId, variantId] = key.split(':').map(Number);
    const product = products.find(item => Number(item.id) === productId);
    if (!product) return [];
    const variant = variantId
      ? product.variants.find(item => Number(item.id) === variantId)
      : null;
    if (variantId && !variant) return [];
    return [{product, variant, quantity, unitPrice: Number(variant?.price ?? product.price)}];
  });
}

function renderSummary() {
  const items = getItems();
  const total = items.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0);
  itemList.innerHTML = items.length ? items.map(({product, variant, quantity, unitPrice}) => `
    <div class="checkout-item">
      <span>${escapeHtml(product.name)}${variant ? ` (${escapeHtml(variant.size)})` : ''} × ${fa(quantity)}</span>
      <b>${money(unitPrice * quantity)}</b>
    </div>`).join('') : '<p class="note">سبد خرید خالی است. ابتدا محصولی به سبد اضافه کنید.</p>';
  totalElement.textContent = money(total);
  submitButton.disabled = !items.length;
  return items;
}

async function loadProducts() {
  try {
    const response = await fetch(form.dataset.productsUrl, {headers: {Accept: 'application/json'}});
    if (!response.ok) throw new Error(`Products API returned ${response.status}`);
    const data = await response.json();
    products = data.products;
    const items = renderSummary();
    if (Object.keys(cart).length && !items.length) {
      messageElement.textContent = 'محصولات سبد خرید در دسترس نیستند؛ به فروشگاه برگردید و سبد را بررسی کنید.';
    }
  } catch (error) {
    console.error('Could not load products for checkout.', error);
    itemList.innerHTML = '<p class="note">بارگذاری محصولات ممکن نشد. صفحه را دوباره بارگذاری کنید.</p>';
    messageElement.textContent = 'دریافت اطلاعات سبد خرید با خطا روبه‌رو شد.';
  }
}

form.addEventListener('change', event => {
  if (event.target.name === 'payment') messageElement.textContent = '';
});

form.addEventListener('submit', event => {
  event.preventDefault();
  messageElement.textContent = '';
  if (!form.reportValidity()) return;

  const payment = form.elements.payment.value;
  if (payment === 'gateway') {
    messageElement.textContent = 'درگاه پرداخت هنوز فعال نشده است. لطفاً فعلاً روش کارت‌به‌کارت را انتخاب کنید.';
    return;
  }

  const items = renderSummary();
  if (!items.length) {
    messageElement.textContent = 'سبد خرید خالی است یا محصولات آن در دسترس نیستند.';
    return;
  }

  const data = new FormData(form);
  const phone = normalizeDigits(String(data.get('phone'))).replace(/\s/g, '');
  const postalCode = normalizeDigits(String(data.get('postal_code')));
  const lines = items.map(({product, variant, quantity, unitPrice}) =>
    `• ${product.name}${variant ? ` (${variant.size})` : ''} × ${fa(quantity)} = ${money(unitPrice * quantity)}`);
  const total = items.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0);
  const address = `${data.get('province')}، ${data.get('city')}، ${data.get('address')}`;
  const notes = String(data.get('notes')).trim();
  const message = [
    'سلام، سفارش جدید از سایت آسمان شب:',
    ...lines,
    `جمع کل: ${money(total)}`,
    '',
    `نام و نام خانوادگی: ${String(data.get('name')).trim()}`,
    `تلفن: ${phone}`,
    `استان و شهر: ${data.get('province')}، ${data.get('city')}`,
    `آدرس: ${address}`,
    `کد پستی: ${postalCode}`,
    'روش پرداخت: کارت‌به‌کارت',
    ...(notes ? [`توضیحات: ${notes}`] : []),
  ].join('\n');
  const telegramOrderId = form.dataset.telegramOrderId;
  window.open(
    `https://t.me/${encodeURIComponent(telegramOrderId)}?text=${encodeURIComponent(message)}`,
    '_blank',
    'noopener',
  );
});

loadProducts();
