import re

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_delete
from django.conf import settings
from django.dispatch import receiver


def validate_css_color(value):
    value = value.strip()
    if re.fullmatch(r"#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})", value):
        return

    match = re.fullmatch(r"rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)", value, re.IGNORECASE)
    if match and all(int(channel) <= 255 for channel in match.groups()):
        return

    raise ValidationError("رنگ را با فرمت HEX یا RGB معتبر وارد کنید؛ مانند #351321 یا rgb(53, 19, 33).")


class Category(models.Model):
    name = models.CharField("نام", max_length=80, unique=True)
    slug = models.SlugField("شناسه", unique=True, allow_unicode=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"

    def __str__(self): return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="دسته‌بندی")
    name = models.CharField("نام محصول", max_length=160)
    description = models.TextField("توضیحات", blank=True)
    price = models.PositiveIntegerField("قیمت (تومان)")
    old_price = models.PositiveIntegerField("قیمت قبل", blank=True, null=True)
    stock = models.PositiveIntegerField("موجودی", default=0)
    image = models.ImageField("تصویر", upload_to="products/", blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصول‌ها"
        ordering = ["-created_at"]

    def __str__(self): return self.name

    @property
    def price_range(self):
        prices = [variant.price for variant in self.variants.all()]
        return (min(prices), max(prices)) if prices else None


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="gallery_images",
        verbose_name="محصول",
    )
    image = models.ImageField("تصویر", upload_to="products/gallery/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تصویر گالری محصول"
        verbose_name_plural = "تصاویر گالری محصول"
        ordering = ["id"]

    def __str__(self):
        return f"تصویر گالری {self.product.name} #{self.pk}"


@receiver(pre_delete, sender=ProductImage)
def delete_product_gallery_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


@receiver(pre_delete, sender=Product)
def delete_product_main_image_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants", verbose_name="محصول")
    size = models.CharField("سایز", max_length=80)
    price = models.PositiveIntegerField("قیمت (تومان)")
    old_price = models.PositiveIntegerField("قیمت قبل", blank=True, null=True)

    class Meta:
        verbose_name = "سایز محصول"
        verbose_name_plural = "سایزهای محصول"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=("product", "size"), name="unique_product_variant_size"),
        ]

    def __str__(self): return f"{self.product.name} - {self.size}"


class SiteSettings(models.Model):
    brand_name = models.CharField("نام برند / لوگو", max_length=80, default="آسمان شب")
    meta_title = models.CharField("عنوان صفحه مرورگر", max_length=180, default="آسمان شب | فروشگاه تابلو و هدیه")
    hero_image = models.ImageField("عکس اصلی صفحه", upload_to="site/", blank=True)
    hero_text = models.TextField("متن زیر عکس ماه", default="تابلوهای هوشمند، گل‌های مخملی، چراغ خواب و هدیه‌های آماده. هر چیزی که شب‌های خانه‌تان را آرام‌تر می‌کند.")
    primary_cta_text = models.CharField("متن دکمه اول", max_length=60, default="مشاهده محصولات")
    primary_cta_link = models.CharField("لینک دکمه اول", max_length=200, default="#shop")
    secondary_cta_text = models.CharField("متن دکمه دوم", max_length=80, default="ثبت سفارش در تلگرام")
    secondary_cta_link = models.CharField("لینک دکمه دوم", max_length=200, default="https://t.me/tablo_aseman_shab")
    shop_title = models.CharField("عنوان بخش محصولات", max_length=80, default="محصولات")
    shop_subtitle = models.CharField("زیرعنوان بخش محصولات", max_length=160, default="مجموعه‌ی آسمان شب")
    inspiration_card_1 = models.CharField("متن کارت اول", max_length=200, default="You bought a smile from us, not our products.")
    inspiration_card_2 = models.CharField("متن کارت دوم", max_length=200, default="May every little light lead you somewhere beautiful.")
    inspiration_card_3 = models.CharField("متن کارت سوم", max_length=200, default="Keep a little wonder close to your heart.")
    inspiration_card_4 = models.CharField("متن کارت چهارم", max_length=200, default="Let the quiet moments become your favorite memories.")
    inspiration_card_color = models.CharField(
        "رنگ کارت‌ها",
        max_length=32,
        default="#351321",
        validators=[validate_css_color],
    )
    inspiration_text_color = models.CharField(
        "رنگ نوشته کارت‌ها",
        max_length=32,
        default="#f4e8df",
        validators=[validate_css_color],
    )
    inspiration_hatch = models.BooleanField("نمایش هاشور روی کارت‌ها", default=True)
    track_title = models.CharField("عنوان بخش پیگیری", max_length=80, default="پیگیری سفارش")
    track_subtitle = models.CharField("زیرعنوان بخش پیگیری", max_length=200, default="شماره سفارش و چهار رقم آخر شماره تلفن را وارد کنید.")
    order_title = models.CharField("عنوان بخش نحوه سفارش", max_length=80, default="نحوه سفارش")
    order_subtitle = models.CharField("زیرعنوان بخش نحوه سفارش", max_length=200, default="بدون ثبت‌نام؛ سبد را پر کنید و سفارش را در تلگرام نهایی کنید.")
    footer_brand = models.CharField("نام برند فوتر", max_length=80, default="آسمان شب")
    footer_text = models.TextField("متن فوتر", default="تابلو، گل و هدیه. ارسال به سراسر کشور.")
    footer_order_label = models.CharField("برچسب ثبت سفارش", max_length=40, default="ثبت سفارش:")
    telegram_order_id = models.CharField(
        "شناسه تلگرام ثبت سفارش",
        max_length=32,
        default="tablo_aseman_shab",
    )
    footer_order_text = models.CharField("نام کاربری سفارش", max_length=80, default="@tablo_aseman_shab")
    footer_order_link = models.CharField("لینک سفارش", max_length=200, default="https://t.me/tablo_aseman_shab")
    footer_channel_label = models.CharField("برچسب کانال", max_length=40, default="کانال تلگرام:")
    footer_channel_text = models.CharField("نام کانال", max_length=80, default="aseman_shab_ir")
    footer_channel_link = models.CharField("لینک کانال", max_length=200, default="https://t.me/aseman_shab_ir")

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def __str__(self): return self.brand_name

    @property
    def telegram_order_link(self):
        return f"https://t.me/{self.telegram_order_id}"

    @property
    def telegram_order_username(self):
        return f"@{self.telegram_order_id}"

    @classmethod
    def get(cls):
        site = cls.objects.first()
        if site is None:
            site = cls.objects.create()
        return site


class SocialLink(models.Model):
    class Icon(models.TextChoices):
        TELEGRAM = "telegram", "تلگرام"
        INSTAGRAM = "instagram", "اینستاگرام"
        WHATSAPP = "whatsapp", "واتساپ"
        FACEBOOK = "facebook", "فیسبوک"
        X = "x", "ایکس (X)"
        YOUTUBE = "youtube", "یوتیوب"
        TIKTOK = "tiktok", "تیک‌تاک"
        LINK = "link", "لینک عمومی"

    site = models.ForeignKey(SiteSettings, on_delete=models.CASCADE, related_name="social_links")
    label = models.CharField("عنوان", max_length=60)
    icon = models.CharField("آیکون", max_length=16, choices=Icon.choices, default=Icon.LINK)
    url = models.URLField("لینک", max_length=500)
    position = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "شبکه اجتماعی فوتر"
        verbose_name_plural = "شبکه‌های اجتماعی فوتر"

    def __str__(self):
        return self.label


class PageView(models.Model):
    created_at = models.DateTimeField("زمان بازدید", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "بازدید صفحه"
        verbose_name_plural = "بازدیدهای صفحه"


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    phone = models.CharField("تلفن", max_length=20, unique=True)

    class Meta:
        verbose_name = "حساب مشتری"
        verbose_name_plural = "حساب‌های مشتری"

    def __str__(self):
        return self.user.get_full_name() or self.user.email


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "جدید"
        PREPARING = "preparing", "در حال آماده‌سازی"
        SENT = "sent", "ارسال‌شده"
        DELIVERED = "delivered", "تحویل‌شده"
        CANCELLED = "cancelled", "لغوشده"
    customer_name = models.CharField("نام مشتری", max_length=120)
    phone = models.CharField("تلفن", max_length=20)
    address = models.TextField("نشانی")
    status = models.CharField("وضعیت", max_length=12, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ["-created_at"]

    def __str__(self): return f"سفارش #{self.pk} - {self.customer_name}"

    @property
    def total_amount(self):
        return sum(item.total for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant_name = models.CharField("سایز", max_length=80, blank=True)
    quantity = models.PositiveIntegerField("تعداد", default=1)
    unit_price = models.PositiveIntegerField("قیمت واحد (تومان)")

    @property
    def total(self): return self.quantity * self.unit_price
