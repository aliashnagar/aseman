const $ = selector => document.querySelector(selector);
const fa = value => Number(value || 0).toLocaleString('fa-IR');
const money = value => `${fa(value)} تومان`;
const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[char]));
const normalizeDigits = value => value
  .replace(/[۰-۹]/g, digit => String(digit.charCodeAt(0) - 1776))
  .replace(/[٠-٩]/g, digit => String(digit.charCodeAt(0) - 1632));
const readStorage = (key, fallback) => {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
};

const grid = $('#grid');
const search = $('#q');
const sort = $('#so');
let products = [];
let onlyWish = false;
let cart = readStorage('as_cart', {});
let wish = readStorage('as_wish', []);

if (!cart || Array.isArray(cart) || typeof cart !== 'object') cart = {};
if (!Array.isArray(wish)) wish = [];
wish = wish.map(Number).filter(Number.isFinite);
cart = Object.fromEntries(Object.entries(cart)
  .map(([id, quantity]) => [id, Number(quantity)])
  .filter(([, quantity]) => Number.isInteger(quantity) && quantity > 0));

function toast(message) {
  const element = $('#ts');
  if (!element) return;
  element.textContent = message;
  element.classList.add('on');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove('on'), 1800);
}

function saveStorage() {
  try {
    localStorage.setItem('as_cart', JSON.stringify(cart));
    localStorage.setItem('as_wish', JSON.stringify(wish));
  } catch {
    toast('ذخیره در مرورگر ممکن نیست؛ فضای ذخیره‌سازی را بررسی کنید.');
  }
}

function productById(id) {
  return products.find(product => Number(product.id) === Number(id));
}

function cartEntry(key) {
  const [productId, variantId] = String(key).split(':').map(Number);
  return {productId, variantId: variantId || null};
}

function variantById(product, id) {
  return product.variants?.find(variant => Number(variant.id) === Number(id));
}

function itemPrice(product, variantId) {
  return variantId ? variantById(product, variantId)?.price : product.price;
}

function art(product) {
  if (product.image_url) {
    return `<img src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.name)}" loading="lazy">`;
  }
  return '<span class="art-placeholder" aria-hidden="true">☾</span>';
}

function price(product) {
  const oldPrice = Number(product.old_price);
  const currentPrice = money(product.price);
  return oldPrice > Number(product.price)
    ? `<s>${money(oldPrice)}</s> ${currentPrice}`
    : currentPrice;
}

function variantPrice(variant) {
  const oldPrice = Number(variant.old_price);
  const currentPrice = money(variant.price);
  return oldPrice > Number(variant.price)
    ? `<s>${money(oldPrice)}</s> ${currentPrice}`
    : currentPrice;
}

function catalogPrice(product) {
  if (!product.variants?.length) return price(product);
  const lowest = Math.min(...product.variants.map(variant => Number(variant.price)));
  return `از ${money(lowest)}`;
}

function render() {
  if (!grid) return;
  const query = search.value.trim().toLocaleLowerCase('fa');
  const shown = products.filter(product => {
    const matchesWish = !onlyWish || wish.includes(Number(product.id));
    const text = `${product.name} ${product.description}`.toLocaleLowerCase('fa');
    return matchesWish && (!query || text.includes(query));
  });
  const lowestPrice = product => product.variants?.length
    ? Math.min(...product.variants.map(variant => Number(variant.price)))
    : Number(product.price);
  if (sort.value === '0') shown.sort((a, b) => Number(b.sold_quantity) - Number(a.sold_quantity));
  if (sort.value === '1') shown.sort((a, b) => lowestPrice(a) - lowestPrice(b));
  if (sort.value === '2') shown.sort((a, b) => lowestPrice(b) - lowestPrice(a));

  grid.innerHTML = shown.length ? shown.map(product => {
    const id = Number(product.id);
    return `<article class="card">
      <div class="card-media">
        <button class="art" type="button" data-product-detail="${id}" aria-label="${escapeHtml(product.name)}">${art(product)}</button>
        <button class="ibtn wish" type="button" data-wish="${id}" aria-label="علاقه‌مندی" aria-pressed="${wish.includes(id)}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/></svg>
        </button>
      </div>
      <h3>${escapeHtml(product.name)}</h3>
      <div class="meta"><span class="price">${catalogPrice(product)}</span>
        <button class="add" type="button" ${product.variants?.length
          ? `data-product-detail="${id}">انتخاب سایز`
          : `data-add="${id}">افزودن به سبد`}</button>
      </div>
    </article>`;
  }).join('') : `<p class="empty">${onlyWish
    ? 'هنوز محصولی را به علاقه‌مندی‌ها اضافه نکرده‌اید.'
    : 'محصولی با این مشخصات پیدا نشد. عبارت جستجو را تغییر دهید.'}</p>`;

  $('#cn').textContent = Object.values(cart).reduce((total, quantity) => total + quantity, 0) || '';
  $('#wn').textContent = wish.length || '';
  $('#wl').setAttribute('aria-pressed', String(onlyWish));
}

function drawCart() {
  const itemList = $('#items');
  if (!itemList) return;
  const validItems = Object.entries(cart).filter(([key]) => {
    const {productId, variantId} = cartEntry(key);
    const product = productById(productId);
    return product && (!variantId || variantById(product, variantId));
  });
  if (validItems.length !== Object.keys(cart).length) {
    cart = Object.fromEntries(validItems);
    saveStorage();
  }
  let total = 0;
  itemList.innerHTML = validItems.length ? validItems.map(([key, quantity]) => {
    const {productId, variantId} = cartEntry(key);
    const product = productById(productId);
    const variant = variantId ? variantById(product, variantId) : null;
    const unitPrice = Number(itemPrice(product, variantId));
    const subtotal = unitPrice * quantity;
    total += subtotal;
    return `<div class="row">
      <div class="th">${art(product)}</div>
      <div><h4>${escapeHtml(product.name)}</h4>${variant ? `<small>سایز: ${escapeHtml(variant.size)}</small><br>` : ''}<small>${money(unitPrice)}</small><br>
        <span class="qty">
          <button type="button" data-quantity="${key}|1" aria-label="افزایش تعداد">+</button>
          <span>${fa(quantity)}</span>
          <button type="button" data-quantity="${key}|-1" aria-label="کاهش تعداد">−</button>
        </span>
      </div>
      <button class="rm" type="button" data-remove="${key}">حذف</button>
    </div>`;
  }).join('') : '<p class="empty" style="padding:30px 0">سبد خرید خالی است. از بخش محصولات چیزی اضافه کنید.</p>';
  $('#tt').textContent = money(total);
  $('#df').hidden = !validItems.length;
}

function addToCart(id, amount = 1) {
  const product = productById(id);
  if (!product || product.variants?.length) return false;
  cart[id] = (cart[id] || 0) + amount;
  if (cart[id] <= 0) delete cart[id];
  saveStorage();
  render();
  drawCart();
  return true;
}

function addVariantToCart(id, variantId) {
  const product = productById(id);
  if (!product || !variantById(product, variantId)) return false;
  const key = `${id}:${variantId}`;
  cart[key] = (cart[key] || 0) + 1;
  saveStorage();
  render();
  drawCart();
  return true;
}

function setDrawer(open) {
  const drawer = $('#dr');
  drawer.classList.toggle('on', open);
  $('#ov').classList.toggle('on', open);
  drawer.setAttribute('aria-hidden', String(!open));
  if (open) {
    drawCart();
    $('#dc').focus();
  }
}

function showProduct(id) {
  const product = productById(id);
  if (!product) return;
  const dialog = $('#dg');
  const variants = product.variants || [];
  const firstVariant = variants[0];
  dialog.innerHTML = `<div class="pd">
    <div class="art">${art(product)}</div>
    <div>
      <h2>${escapeHtml(product.name)}</h2>
      ${variants.length
        ? `<label class="variant-picker">انتخاب سایز
          <select id="selected-variant">${variants.map(variant =>
            `<option value="${Number(variant.id)}">${escapeHtml(variant.size)}</option>`).join('')}</select>
        </label>
        <span class="price" id="selected-variant-price">${variantPrice(firstVariant)}</span>`
        : `<span class="price">${price(product)}</span>`}
      <p>${escapeHtml(product.description)}</p>
      <p>دسته: ${escapeHtml(product.category_name || '')}</p>
      <div class="cta">
        <button class="btn" type="button" data-add="${Number(product.id)}" ${variants.length ? 'data-variant-select' : ''} data-close-dialog>افزودن به سبد</button>
        <button class="btn ghost" type="button" data-close-dialog>بستن</button>
      </div>
    </div>
  </div>`;
  dialog.querySelector('#selected-variant')?.addEventListener('change', event => {
    const variant = variantById(product, event.target.value);
    if (variant) dialog.querySelector('#selected-variant-price').innerHTML = variantPrice(variant);
  });
  dialog.showModal();
}

function updateUrl() {
  const params = new URLSearchParams();
  if (search.value.trim()) params.set('q', search.value.trim());
  if (sort.value !== '0') params.set('sort', sort.value);
  history.replaceState(null, '', `${location.pathname}${params.size ? `?${params}` : ''}${location.hash}`);
}

function renderTrackingResult(order, container) {
  const statuses = ['جدید', 'در حال آماده‌سازی', 'ارسال‌شده', 'تحویل‌شده'];
  const statusIndex = statuses.indexOf(order.status);
  if (order.status === 'لغوشده') {
    return `<div class="tkr"><h3>سفارش شماره ${fa(order.id)}</h3><p>${escapeHtml(order.created_at)}</p><p class="bad">این سفارش لغو شده است. برای اطلاعات بیشتر در تلگرام پیام دهید.</p></div>`;
  }
  const activeStatus = Math.max(0, statusIndex);
  return `<div class="tkr">
    <h3>سفارش شماره ${fa(order.id)}</h3>
    <p>ثبت‌شده در ${escapeHtml(order.created_at)}</p>
    <p style="margin-top:6px;color:var(--moon)">${escapeHtml(order.items || '')}</p>
    <div class="tl">${statuses.map((status, index) => `<div class="${index <= activeStatus ? 'on' : ''}"><i></i>${status}</div>`).join('')}</div>
    <p style="margin-top:16px">وضعیت فعلی: <b style="color:var(--moon)">${escapeHtml(order.status)}</b></p>
  </div>`;
}

async function loadProducts() {
  try {
    const response = await fetch('/api/products/', {headers: {Accept: 'application/json'}});
    if (!response.ok) throw new Error(`Products API returned ${response.status}`);
    const data = await response.json();
    products = data.products;
    render();
  } catch {
    grid.innerHTML = '<p class="empty">دریافت محصولات ممکن نیست. صفحه را دوباره بارگذاری کنید.</p>';
  }
}

if (grid) {
  if (search) search.value = new URLSearchParams(location.search).get('q') || search.value;
  if (new URLSearchParams(location.search).has('sort')) sort.value = new URLSearchParams(location.search).get('sort');
  search.addEventListener('input', () => { render(); updateUrl(); });
  sort.addEventListener('change', () => { render(); updateUrl(); });
  loadProducts();
}

document.addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.dataset.add) {
    const added = button.hasAttribute('data-variant-select')
      ? addVariantToCart(button.dataset.add, $('#selected-variant').value)
      : addToCart(button.dataset.add);
    if (added) {
      toast('به سبد خرید اضافه شد');
      if (button.hasAttribute('data-close-dialog')) $('#dg').close();
    }
  }
  if (button.dataset.productDetail) showProduct(button.dataset.productDetail);
  if (button.dataset.wish) {
    const id = Number(button.dataset.wish);
    wish = wish.includes(id) ? wish.filter(item => item !== id) : [...wish, id];
    saveStorage();
    render();
  }
  if (button.dataset.quantity) {
    const [key, amount] = button.dataset.quantity.split('|');
    cart[key] = (cart[key] || 0) + Number(amount);
    if (cart[key] <= 0) delete cart[key];
    saveStorage();
    render();
    drawCart();
  }
  if (button.dataset.remove) {
    delete cart[button.dataset.remove];
    saveStorage();
    render();
    drawCart();
  }
  if (button.id === 'cb') setDrawer(true);
  if (button.id === 'dc') setDrawer(false);
  if (button.id === 'wl') {
    onlyWish = !onlyWish;
    $('#shop').scrollIntoView();
    render();
    updateUrl();
    toast(onlyWish ? 'فقط علاقه‌مندی‌ها' : 'همه محصولات');
  }
});

$('#ov')?.addEventListener('click', () => setDrawer(false));
$('#dg')?.addEventListener('click', event => {
  if (event.target === $('#dg')) $('#dg').close();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') setDrawer(false);
});

$('#go')?.addEventListener('click', () => {
  const name = $('#fn').value.trim();
  const phone = normalizeDigits($('#fp').value.trim()).replace(/\s/g, '');
  const address = $('#fa').value.trim();
  const error = $('#er');
  if (!name || !/^[0-9+]{10,14}$/.test(phone) || address.length < 8) {
    error.textContent = 'نام، شماره تماس معتبر و آدرس کامل را وارد کنید.';
    return;
  }
  const items = Object.entries(cart).filter(([key]) => {
    const {productId, variantId} = cartEntry(key);
    const product = productById(productId);
    return product && (!variantId || variantById(product, variantId));
  });
  if (!items.length) {
    error.textContent = 'سبد خرید شما خالی است.';
    return;
  }
  error.textContent = '';
  let total = 0;
  const lines = items.map(([key, quantity]) => {
    const {productId, variantId} = cartEntry(key);
    const product = productById(productId);
    const variant = variantId ? variantById(product, variantId) : null;
    const unitPrice = Number(itemPrice(product, variantId));
    const subtotal = unitPrice * quantity;
    total += subtotal;
    return `• ${product.name}${variant ? ` (${variant.size})` : ''} × ${fa(quantity)} = ${money(subtotal)}`;
  });
  const message = `سلام، سفارش جدید از سایت آسمان شب:\n${lines.join('\n')}\nجمع کل: ${money(total)}\n\nنام: ${name}\nتلفن: ${phone}\nآدرس: ${address}`;
  window.open(`https://t.me/tablo_aseman_shab?text=${encodeURIComponent(message)}`, '_blank', 'noopener');
});

const canvas = $('#sky');
if (canvas) {
  const context = canvas.getContext('2d');
  let stars = [];
  let width = 0;
  let height = 0;
  const resize = () => {
    const ratio = window.devicePixelRatio || 1;
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    const count = Math.min(600, Math.round(width * height / 6500));
    stars = Array.from({length: count}, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 1.2 + 0.25,
      alpha: Math.random() * 0.6 + 0.25,
      speed: Math.random() * 0.0015 + 0.0004,
      offset: Math.random() * 6,
    }));
  };
  const paint = time => {
    context.clearRect(0, 0, width, height);
    stars.forEach(star => {
      context.globalAlpha = Math.max(0.08, star.alpha + Math.sin(time * star.speed + star.offset) * 0.25);
      context.fillStyle = '#efe9dc';
      context.beginPath();
      context.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
      context.fill();
    });
    context.globalAlpha = 1;
  };
  resize();
  window.addEventListener('resize', resize);
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    paint(0);
  } else {
    const animate = time => {
      paint(time);
      window.requestAnimationFrame(animate);
    };
    window.requestAnimationFrame(animate);
  }
}
