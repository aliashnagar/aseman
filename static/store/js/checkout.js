const form = document.querySelector('#checkout-form');
const itemList = document.querySelector('#checkout-items');
const totalElement = document.querySelector('#checkout-total');
const shippingElement = document.querySelector('#checkout-shipping');
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
let shippingCost = 0;
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
  const quantityByProduct = new Map();
  items.forEach(item => quantityByProduct.set(
    Number(item.product.id),
    (quantityByProduct.get(Number(item.product.id)) || 0) + item.quantity,
  ));
  const hasUnavailableItems = items.some(item =>
    Number(item.product.stock) < quantityByProduct.get(Number(item.product.id)));
  const subtotal = items.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0);
  itemList.innerHTML = items.length ? items.map(({product, variant, quantity, unitPrice}) => `
    <div class="checkout-item">
      <span>${escapeHtml(product.name)}${variant ? ` (${escapeHtml(variant.size)})` : ''} × ${fa(quantity)}${Number(product.stock) < quantity ? ' (ناموجود یا ناکافی)' : ''}</span>
      <b>${Number(product.stock) > 0 ? money(unitPrice * quantity) : 'ناموجود'}</b>
    </div>`).join('') : '<p class="note">سبد خرید خالی است. ابتدا محصولی به سبد اضافه کنید.</p>';
  shippingElement.textContent = money(shippingCost);
  totalElement.textContent = money(subtotal + shippingCost);
  submitButton.disabled = !items.length || hasUnavailableItems;
  if (hasUnavailableItems) messageElement.textContent = 'موجودی یک یا چند محصول سبد خرید کافی نیست؛ سبد را اصلاح کنید.';
  return items;
}

async function loadProducts() {
  try {
    const response = await fetch(form.dataset.productsUrl, {headers: {Accept: 'application/json'}});
    if (!response.ok) throw new Error(`Products API returned ${response.status}`);
    const data = await response.json();
    products = data.products;
    shippingCost = Number(data.shipping_cost || 0);
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
  if (!items.length || submitButton.disabled) {
    messageElement.textContent = 'سبد خرید خالی است یا محصولات آن در دسترس نیستند.';
    return;
  }

  const data = new FormData(form);
  const phone = normalizeDigits(String(data.get('phone'))).replace(/\s/g, '');
  const postalCode = normalizeDigits(String(data.get('postal_code')));
  const provinceAndCity = `${String(data.get('province')).trim()}، ${String(data.get('city')).trim()}`;
  const paymentMethod = payment === 'card_transfer' ? 'کارت‌به‌کارت' : 'درگاه پرداخت';
  const notes = String(data.get('notes')).trim();
  const telegramOrderId = form.dataset.telegramOrderId;
  const telegramWindow = window.open('', '_blank');
  submitButton.disabled = true;
  submitButton.textContent = 'در حال ثبت سفارش…';

  fetch(form.dataset.submitUrl, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': form.querySelector('[name="csrfmiddlewaretoken"]').value,
      Accept: 'application/json',
    },
    body: JSON.stringify({
      name: String(data.get('name')).trim(),
      phone,
      province: String(data.get('province')).trim(),
      city: String(data.get('city')).trim(),
      address: String(data.get('address')).trim(),
      postal_code: postalCode,
      payment,
      cart,
    }),
  }).then(async response => {
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'ثبت سفارش انجام نشد.');
    const lines = result.items.map(item =>
      `• ${item.name}${item.variant ? ` (${item.variant})` : ''} × ${fa(item.quantity)} = ${money(item.total)}`);
    const message = [
      '🌙✨ **سفارش جدید از آسمان شب**',
      'یک خرید دوست‌داشتنی در انتظار تکمیل شدنه! 💜',
      '',
      `🧾 **شماره سفارش:** ${fa(result.order_id)}`,
      '🛍 **محصولات سفارش:**',
      ...lines,
      `💰 مبلغ محصولات: ${money(result.subtotal)}`,
      `🚚 هزینه ارسال: ${money(result.shipping_cost)}`,
      `**مبلغ کل: ${money(result.total)}**`,
      '',
      '👤 **مشخصات گیرنده:**',
      `نام: ${String(data.get('name')).trim()}`,
      `شماره تماس: ${phone}`,
      `استان و شهر: ${provinceAndCity}`,
      `آدرس کامل: ${String(data.get('address')).trim()}`,
      `کد پستی: ${postalCode}`,
      `💳 روش پرداخت: ${paymentMethod}`,
      ...(notes ? [`توضیحات: ${notes}`] : []),
      'ــــــــــــــــــــ',
      '💌 ممنون از اعتمادتون به آسمان شب!',
      'سفارش شما پس از بررسی و تأیید نهایی، وارد مراحل آماده‌سازی می‌شه.',
      'با آرزوی لحظاتی پر از زیبایی و شادی برای شما 🌙',
    ].join('\n');
    cart = {};
    localStorage.removeItem('as_cart');
    if (telegramWindow) {
      telegramWindow.location.href = `https://t.me/${encodeURIComponent(telegramOrderId)}?text=${encodeURIComponent(message)}`;
    }
    messageElement.textContent = `سفارش شماره ${fa(result.order_id)} ثبت شد${telegramWindow ? '؛ پیام تلگرام آماده است.' : '؛ تلگرام باز نشد، لطفاً با پشتیبانی تماس بگیرید.'}`;
  }).catch(error => {
    telegramWindow?.close();
    messageElement.textContent = error.message || 'ثبت سفارش با خطا روبه‌رو شد؛ دوباره تلاش کنید.';
  }).finally(() => {
    submitButton.disabled = false;
    submitButton.textContent = 'ثبت سفارش';
    renderSummary();
  });
});

loadProducts();
