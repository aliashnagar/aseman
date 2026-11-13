from datetime import datetime, time, timedelta
from functools import wraps
import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, F, ProtectedError, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AdminCreationForm,
    CategoryForm,
    CustomerRegistrationForm,
    FAQForm,
    OrderForm,
    OrderItemFormSetFactory,
    ProductForm,
    ProductVariantFormSetFactory,
    SocialLinkFormSetFactory,
    normalize_phone,
)
from .forms import SiteSettingsForm
from .models import Category, CustomerProfile, FAQ, Order, OrderItem, PageView, Product, ProductImage, ProductVariant, SiteSettings


class InsufficientInventory(Exception):
    pass


def panel_login_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if hasattr(request.user, "customer_profile"):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def home(request):
    PageView.objects.create()
    query = request.GET.get("q", "").strip()
    selected_category = request.GET.get("category", "")
    site = SiteSettings.get()
    categories = Category.objects.filter(products__is_active=True).distinct().order_by("name")
    return render(request, "store/home.html", {
        "query": query,
        "site": site,
        "categories": categories,
        "selected_category": selected_category,
        "faq_items": FAQ.objects.all(),
    })


def checkout(request):
    return render(request, "store/checkout.html", {"site": SiteSettings.get()})


def checkout_submit(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "اطلاعات سفارش معتبر نیست."}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"error": "اطلاعات سفارش معتبر نیست."}, status=400)

    name = str(data.get("name", "")).strip()
    phone = normalize_phone(str(data.get("phone", "")))
    province = str(data.get("province", "")).strip()
    city = str(data.get("city", "")).strip()
    address = str(data.get("address", "")).strip()
    postal_code = str(data.get("postal_code", "")).translate(str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789",
    ))
    cart_data = data.get("cart")
    if (
        not name or len(name) > 120 or len(phone) < 4 or not phone.lstrip("+").isdigit()
        or not province or not city or len(address) < 8
        or len(postal_code) != 10 or not postal_code.isdecimal()
        or data.get("payment") != "card_transfer"
        or not isinstance(cart_data, dict) or not cart_data or len(cart_data) > 50
    ):
        return JsonResponse({"error": "مشخصات گیرنده، روش پرداخت یا سبد خرید را بررسی کنید."}, status=400)

    requested_items = []
    quantities_by_product = {}
    for key, quantity in cart_data.items():
        if not isinstance(key, str) or type(quantity) is not int or quantity < 1 or quantity > 99:
            return JsonResponse({"error": "تعداد محصولات سفارش معتبر نیست."}, status=400)
        identifiers = key.split(":")
        if len(identifiers) not in (1, 2) or not all(value.isdecimal() for value in identifiers):
            return JsonResponse({"error": "محصول انتخاب‌شده معتبر نیست."}, status=400)
        product_id = int(identifiers[0])
        variant_id = int(identifiers[1]) if len(identifiers) == 2 else None
        if product_id < 1 or (variant_id is not None and variant_id < 1):
            return JsonResponse({"error": "محصول انتخاب‌شده معتبر نیست."}, status=400)
        requested_items.append((product_id, variant_id, quantity))
        quantities_by_product[product_id] = quantities_by_product.get(product_id, 0) + quantity

    try:
        with transaction.atomic():
            site = SiteSettings.get()
            products = Product.objects.select_for_update().filter(
                pk__in=quantities_by_product,
                is_active=True,
            ).prefetch_related("variants").in_bulk()
            if len(products) != len(quantities_by_product):
                return JsonResponse({"error": "یک یا چند محصول دیگر در دسترس نیستند."}, status=400)
            variant_ids = [variant_id for _, variant_id, _ in requested_items if variant_id]
            variants = ProductVariant.objects.select_for_update().filter(pk__in=variant_ids).in_bulk()
            resolved_items = []
            for product_id, variant_id, quantity in requested_items:
                product = products[product_id]
                variant = variants.get(variant_id) if variant_id else None
                if (variant_id and (not variant or variant.product_id != product_id)) or (
                    product.variants.exists() and not variant
                ):
                    return JsonResponse({"error": "سایز انتخاب‌شده برای محصول معتبر نیست."}, status=400)
                resolved_items.append((product, variant, quantity))
            shortages = [
                product for product_id, quantity in quantities_by_product.items()
                if (product := products[product_id]).stock < quantity
            ]
            if shortages:
                return JsonResponse({"error": "موجودی یک یا چند محصول کافی نیست؛ سبد را اصلاح کنید."}, status=409)
            for product_id, quantity in quantities_by_product.items():
                if not Product.objects.filter(pk=product_id, stock__gte=quantity).update(
                    stock=F("stock") - quantity,
                ):
                    raise InsufficientInventory

            order = Order.objects.create(
                customer_name=name,
                phone=phone,
                address=f"{province}، {city}، {address}",
                status=Order.Status.NEW,
                inventory_deducted=True,
                shipping_cost=site.shipping_cost,
            )
            response_items = []
            subtotal = 0
            for product, variant, quantity in resolved_items:
                unit_price = variant.price if variant else product.price
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant_name=variant.size if variant else "",
                    quantity=quantity,
                    unit_price=unit_price,
                )
                item_total = unit_price * quantity
                subtotal += item_total
                response_items.append({
                    "name": product.name,
                    "variant": variant.size if variant else "",
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total": item_total,
                })
    except InsufficientInventory:
        return JsonResponse({"error": "موجودی یک یا چند محصول همین حالا تغییر کرد؛ سبد را دوباره بررسی کنید."}, status=409)

    return JsonResponse({
        "order_id": order.pk,
        "items": response_items,
        "subtotal": subtotal,
        "shipping_cost": order.shipping_cost,
        "total": subtotal + order.shipping_cost,
    })


@panel_login_required
def site_settings_edit(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    site = SiteSettings.get()
    form = SiteSettingsForm(request.POST or None, request.FILES or None, instance=site)
    social_formset = SocialLinkFormSetFactory(
        request.POST or None,
        instance=site,
        prefix="footer_socials",
    )
    if request.method == "POST":
        if form.is_valid() and social_formset.is_valid():
            with transaction.atomic():
                form.save()
                social_formset.instance = site
                social_formset.save()
            messages.success(request, "تنظیمات سایت با موفقیت ذخیره شد.")
            return redirect("site_settings")
    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "store/site_settings.html", {
        "form": form,
        "social_formset": social_formset,
        "site": site,
        "active_page": "site",
    })


def products_api(request):
    products = Product.objects.filter(is_active=True).select_related("category").annotate(
        sold_quantity=Sum(
            "orderitem__quantity",
            filter=Q(orderitem__order__status__in=[
                Order.Status.NEW,
                Order.Status.PREPARING,
                Order.Status.SENT,
                Order.Status.DELIVERED,
            ]),
            default=0,
        )
    )
    category = request.GET.get("category")
    query = request.GET.get("q", "").strip()
    if category:
        products = products.filter(category__slug=category)
    if query:
        products = products.filter(name__icontains=query)
    return JsonResponse({"shipping_cost": SiteSettings.get().shipping_cost, "products": [{
        "id": product.id, "name": product.name, "description": product.description,
        "price": product.price, "old_price": product.old_price,
        "stock": product.stock,
        "sold_quantity": product.sold_quantity,
        "variants": [{
            "id": variant.id, "size": variant.size, "price": variant.price,
            "old_price": variant.old_price,
        } for variant in product.variants.all()],
        "category": product.category.slug,
        "category_name": product.category.name,
        "image_url": request.build_absolute_uri(product.image.url) if product.image else "",
        "gallery_images": [
            request.build_absolute_uri(image.image.url)
            for image in product.gallery_images.all()
        ],
    } for product in products.prefetch_related("variants", "gallery_images")]})


def login_view(request):
    error = None
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", ""),
            password=request.POST.get("password", ""),
        )
        if user:
            login(request, user)
            return redirect("dashboard")
        error = "\u0646\u0627\u0645 \u06a9\u0627\u0631\u0628\u0631\u06cc \u06cc\u0627 \u0631\u0645\u0632 \u0639\u0628\u0648\u0631 \u0635\u062d\u06cc\u062d \u0646\u06cc\u0633\u062a."
    return render(request, "store/login.html", {"error": error})


def customer_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, "customer_profile"):
            return redirect("customer_dashboard")
        return redirect("dashboard")

    login_error = None
    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()
        password = request.POST.get("password", "")
        if "@" in identifier:
            customer = CustomerProfile.objects.select_related("user").filter(
                user__email__iexact=identifier,
            ).first()
        else:
            phone = normalize_phone(identifier)
            customer = CustomerProfile.objects.select_related("user").filter(phone=phone).first()
        user = authenticate(
            request,
            username=customer.user.username if customer else "",
            password=password,
        )
        if user:
            login(request, user)
            return redirect("customer_dashboard")
        login_error = "ایمیل یا شماره موبایل و رمز عبور را بررسی کنید."
    elif request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])

    return render(request, "store/customer_login.html", {
        "login_error": login_error,
    })


def customer_register(request):
    if request.user.is_authenticated:
        if hasattr(request.user, "customer_profile"):
            return redirect("customer_dashboard")
        return redirect("dashboard")
    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])

    registration_form = CustomerRegistrationForm(request.POST or None)
    if request.method == "POST" and registration_form.is_valid():
        with transaction.atomic():
            user = registration_form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "حساب شما با موفقیت ساخته شد.")
        return redirect("customer_dashboard")
    return render(request, "store/customer_register.html", {
        "registration_form": registration_form,
    })


@login_required(login_url="customer_login")
def customer_dashboard(request):
    try:
        profile = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        return redirect("dashboard")

    password_form = PasswordChangeForm(request.user)
    if request.method == "POST":
        if request.POST.get("action") != "password_change":
            return HttpResponseNotAllowed(["GET", "POST"])
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "رمز عبور با موفقیت تغییر کرد.")
            return redirect("customer_dashboard")
    elif request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])

    orders = Order.objects.filter(phone=profile.phone).prefetch_related("items__product")
    return render(request, "store/customer_dashboard.html", {
        "profile": profile,
        "orders": orders,
        "password_form": password_form,
    })


def logout_view(request):
    logout(request)
    return redirect("home")


@panel_login_required
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "رمز عبور با موفقیت تغییر کرد.")
        return redirect("password_change")
    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "store/password_change.html", {"form": form})


@panel_login_required
def admin_manage(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method == "POST":
        form = AdminCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "حساب ادمین جدید ساخته شد.")
            return redirect("admin_manage")
    elif request.method == "GET":
        form = AdminCreationForm()
    else:
        return HttpResponseNotAllowed(["GET", "POST"])
    users = request.user.__class__.objects.order_by("username")
    return render(request, "store/admin_manage.html", {"form": form, "users": users})


@panel_login_required
def admin_delete(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    user = get_object_or_404(
        request.user.__class__.objects.filter(is_superuser=False),
        pk=pk,
    )
    if user.pk == request.user.pk:
        raise PermissionDenied
    username = user.username
    user.delete()
    messages.success(request, f"حساب ادمین «{username}» حذف شد.")
    return redirect("admin_manage")


@panel_login_required
def dashboard(request):
    now = timezone.localtime()
    today = now.date()
    daily_start = today - timedelta(days=29)
    month_start = (today.replace(day=1) - timedelta(days=335)).replace(day=1)
    year_start = today.replace(year=today.year - 4, month=1, day=1)
    tomorrow = today + timedelta(days=1)

    def chart_series(start, end, truncation, period, label_format):
        counts = {
            (row["period"].date() if isinstance(row["period"], datetime) else row["period"]): row["count"]
            for row in PageView.objects.filter(created_at__gte=start, created_at__lt=end)
            .annotate(period=truncation("created_at"))
            .values("period")
            .annotate(count=Count("pk"))
        }
        values = []
        cursor = period(start.date())
        last = period((end - timedelta(microseconds=1)).date())
        while cursor <= last:
            values.append({"label": label_format(cursor), "value": counts.get(cursor, 0)})
            if truncation is TruncDate:
                cursor += timedelta(days=1)
            elif truncation is TruncMonth:
                cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
            else:
                cursor = cursor.replace(year=cursor.year + 1)
        return values

    start_of_day = lambda value: timezone.make_aware(datetime.combine(value, time.min))
    daily = chart_series(start_of_day(daily_start), start_of_day(tomorrow), TruncDate, lambda value: value, lambda value: value.strftime("%d"))
    monthly = chart_series(start_of_day(month_start), start_of_day(tomorrow), TruncMonth, lambda value: value.replace(day=1), lambda value: str(value.month))
    yearly = chart_series(start_of_day(year_start), start_of_day(tomorrow), TruncYear, lambda value: value.replace(month=1, day=1), lambda value: str(value.year))
    orders = Order.objects.prefetch_related("items__product")
    active_items = OrderItem.objects.filter(order__status__in=[Order.Status.NEW, Order.Status.PREPARING, Order.Status.SENT, Order.Status.DELIVERED])
    sales = active_items.aggregate(value=Sum("quantity"))["value"] or 0
    revenue = active_items.aggregate(value=Sum(F("unit_price") * F("quantity")))["value"] or 0
    today_views = daily[-1]["value"] if daily else 0
    context = {
        "orders": orders[:10],
        "product_count": Product.objects.count(),
        "order_count": orders.count(),
        "new_count": orders.filter(status=Order.Status.NEW).count(),
        "visit_count": sum(row["value"] for row in daily),
        "average_visits": round(sum(row["value"] for row in daily) / len(daily), 1) if daily else 0,
        "today_views": today_views,
        "revenue": revenue,
        "sold_quantity": sales,
        "low_stock": Product.objects.filter(is_active=True, stock__lte=5).order_by("stock", "name")[:10],
        "chart_data": {"d": daily, "m": monthly, "y": yearly},
    }
    return render(request, "store/dashboard.html", context)


@panel_login_required
def product_list(request):
    products = Product.objects.select_related("category").prefetch_related("variants").order_by("name")
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(category__name__icontains=query))
    return render(request, "store/product_list.html", {"products": products, "query": query})


@panel_login_required
def category_list(request):
    next_page = request.GET.get("next")
    if next_page not in ("", "product_add"):
        next_page = ""
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "دسته‌بندی جدید اضافه شد.")
            if request.POST.get("next") == "product_add":
                return redirect("product_add")
            return redirect("category_list")
    elif request.method == "GET":
        form = CategoryForm()
    else:
        return HttpResponseNotAllowed(["GET", "POST"])
    categories = Category.objects.annotate(product_count=Count("products")).order_by("name")
    return render(request, "store/category_list.html", {
        "form": form,
        "categories": categories,
        "next_page": next_page,
    })


@panel_login_required
def faq_manage(request):
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            faq = get_object_or_404(FAQ, pk=request.POST.get("faq_id"))
            faq.delete()
            messages.success(request, "سوال پرتکرار حذف شد.")
            return redirect("faq_manage")
        form = FAQForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "سوال پرتکرار اضافه شد.")
            return redirect("faq_manage")
    elif request.method == "GET":
        form = FAQForm()
    else:
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "store/faq_manage.html", {
        "form": form,
        "faq_items": FAQ.objects.all(),
    })


@panel_login_required
def product_edit(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk is not None else None
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        variant_formset = ProductVariantFormSetFactory(request.POST, instance=product, prefix="variants")
        if form.is_valid() and variant_formset.is_valid():
            clear_image = request.POST.get("clear_image") == "1" and not request.FILES.get("image")
            with transaction.atomic():
                saved_product = form.save()
                variant_formset.instance = saved_product
                discount_percent = form.cleaned_data.get("discount_percent") if form.cleaned_data.get("discount_enabled") else None
                for variant_form in variant_formset.forms:
                    variant_data = variant_form.cleaned_data
                    if not variant_data:
                        continue
                    if variant_data.get("DELETE"):
                        if variant_form.instance.pk:
                            variant_form.instance.delete()
                        continue
                    if not variant_data.get("size"):
                        continue
                    variant = variant_form.save(commit=False)
                    variant.product = saved_product
                    base_price = variant_data["price"]
                    if discount_percent:
                        variant.old_price = base_price
                        variant.price = (base_price * (100 - discount_percent) + 50) // 100
                    else:
                        variant.old_price = None
                        variant.price = base_price
                    variant.save()
                for image in form.cleaned_data["additional_images"]:
                    ProductImage.objects.create(product=saved_product, image=image)
                image_ids_to_remove = request.POST.getlist("remove_images")
                if image_ids_to_remove:
                    images_to_remove = saved_product.gallery_images.filter(pk__in=image_ids_to_remove)
                    for gallery_image in images_to_remove:
                        gallery_image.delete()
                if clear_image and saved_product.image:
                    saved_product.image.delete(save=False)
                    saved_product.image = ""
                    saved_product.save(update_fields=["image"])
            messages.success(request, "محصول ذخیره شد.")
            return redirect("product_list")
    elif request.method == "GET":
        form = ProductForm(instance=product)
        variant_formset = ProductVariantFormSetFactory(instance=product, prefix="variants")
    else:
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "store/product_form.html", {
        "form": form, "product": product, "variant_formset": variant_formset,
        "gallery_images": product.gallery_images.all() if product else [],
    })


@panel_login_required
def product_toggle(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save(update_fields=["is_active"])
    messages.success(request, "وضعیت نمایش محصول تغییر کرد.")
    return redirect("product_list")


@panel_login_required
def product_delete(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    product = get_object_or_404(Product, pk=pk)
    try:
        product.delete()
    except ProtectedError:
        messages.error(request, "این محصول در سفارش ثبت شده و قابل حذف نیست.")
    else:
        messages.success(request, "محصول حذف شد.")
    return redirect("product_list")


@panel_login_required
def order_list(request):
    if request.method == "POST":
        order_id = request.POST.get("order_id")
        status = request.POST.get("status")
        if status not in Order.Status.values:
            messages.error(request, "وضعیت انتخاب‌شده معتبر نیست.")
        else:
            with transaction.atomic():
                order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)
                items = list(order.items.values("product_id").annotate(quantity=Sum("quantity")))
                if order.status == Order.Status.CANCELLED and status != Order.Status.CANCELLED:
                    locked_products = Product.objects.select_for_update().in_bulk(
                        item["product_id"] for item in items
                    )
                    shortages = [
                        item for item in items
                        if locked_products[item["product_id"]].stock < item["quantity"]
                    ]
                    if shortages:
                        messages.error(request, "موجودی کافی برای فعال‌کردن دوباره این سفارش وجود ندارد.")
                        return redirect("order_list")
                    for item in items:
                        Product.objects.filter(pk=item["product_id"]).update(
                            stock=F("stock") - item["quantity"]
                        )
                    order.inventory_deducted = True
                elif status == Order.Status.CANCELLED and order.inventory_deducted:
                    for item in items:
                        Product.objects.filter(pk=item["product_id"]).update(
                            stock=F("stock") + item["quantity"]
                        )
                    order.inventory_deducted = False
                order.status = status
                order.save(update_fields=["status", "inventory_deducted"])
            messages.success(request, f"وضعیت سفارش #{order.pk} به‌روز شد.")
        return redirect("order_list")
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    orders = Order.objects.prefetch_related("items__product")
    return render(request, "store/order_list.html", {"orders": orders, "statuses": Order.Status.choices})


@panel_login_required
def order_add(request):
    order = Order()
    if request.method == "POST":
        form = OrderForm(request.POST, instance=order)
        item_formset = OrderItemFormSetFactory(request.POST, instance=order, prefix="items")
        if form.is_valid() and item_formset.is_valid():
            saved_order = None
            with transaction.atomic():
                requested = {}
                for item_form in item_formset.forms:
                    data = item_form.cleaned_data
                    if data and not data.get("DELETE") and data.get("product"):
                        product_id = data["product"].pk
                        requested[product_id] = requested.get(product_id, 0) + data["quantity"]
                locked_products = Product.objects.select_for_update().in_bulk(requested)
                shortages = {} if form.cleaned_data["status"] == Order.Status.CANCELLED else {
                    product_id: quantity - locked_products[product_id].stock
                    for product_id, quantity in requested.items()
                    if locked_products[product_id].stock < quantity
                }
                if shortages:
                    for item_form in item_formset.forms:
                        data = item_form.cleaned_data
                        product = data.get("product") if data else None
                        if product and product.pk in shortages:
                            item_form.add_error(
                                "quantity",
                                f"موجودی کافی نیست؛ موجودی فعلی {locked_products[product.pk].stock} عدد است.",
                            )
                else:
                    saved_order = form.save()
                    saved_order.shipping_cost = SiteSettings.get().shipping_cost
                    saved_order.save(update_fields=["shipping_cost"])
                    item_formset.instance = saved_order
                    item_formset.save()
                    if saved_order.status != Order.Status.CANCELLED:
                        for product_id, quantity in requested.items():
                            Product.objects.filter(pk=product_id).update(stock=F("stock") - quantity)
                        saved_order.inventory_deducted = True
                        saved_order.save(update_fields=["inventory_deducted"])
            if saved_order:
                messages.success(request, f"سفارش ثبت شد. شماره پیگیری مشتری: {saved_order.pk}")
                return redirect("order_list")
    elif request.method == "GET":
        form = OrderForm(instance=order)
        item_formset = OrderItemFormSetFactory(instance=order, prefix="items")
    else:
        return HttpResponseNotAllowed(["GET", "POST"])
    products = Product.objects.prefetch_related("variants").order_by("name")
    product_data = [{
        "id": product.pk,
        "price": product.price,
        "variants": [{
            "id": variant.pk,
            "size": variant.size,
            "price": variant.price,
        } for variant in product.variants.all()],
    } for product in products]
    return render(request, "store/order_form.html", {
        "form": form,
        "item_formset": item_formset,
        "products_data": product_data,
    })


def track_order(request):
    order = None
    error = None
    if request.method == "POST":
        number = request.POST.get("number", "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        phone = request.POST.get("phone", "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        if not number.isdecimal() or len(phone) != 4 or not phone.isdecimal():
            error = "شماره سفارش و چهار رقم آخر تلفن را بررسی کنید."
        else:
            order = Order.objects.prefetch_related("items__product").filter(pk=number, phone__endswith=phone).first()
            if not order:
                error = "سفارشی با این اطلاعات پیدا نشد."
    status_steps = list(Order.Status.choices)[:-1]
    status_index = next((index for index, (status, _) in enumerate(status_steps) if order and order.status == status), 0)
    return render(request, "store/track.html", {
        "order": order, "error": error, "status_steps": status_steps, "status_index": status_index,
    })
