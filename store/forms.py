import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils.text import slugify

from .models import Category, CustomerProfile, Order, OrderItem, Product, ProductImage, ProductVariant, SiteSettings


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleImageInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [super().clean(upload, initial) for upload in data]


def normalize_phone(value):
    phone = value.translate(str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    ))
    return "".join(character for character in phone if character not in " -()")


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = (
            "brand_name",
            "meta_title",
            "hero_image",
            "hero_text",
            "primary_cta_text",
            "primary_cta_link",
            "secondary_cta_text",
            "secondary_cta_link",
            "shop_title",
            "shop_subtitle",
            "inspiration_card_1",
            "inspiration_card_2",
            "inspiration_card_3",
            "inspiration_card_4",
            "inspiration_card_color",
            "inspiration_text_color",
            "inspiration_hatch",
            "track_title",
            "track_subtitle",
            "order_title",
            "order_subtitle",
            "footer_brand",
            "footer_text",
            "footer_order_label",
            "telegram_order_id",
            "footer_order_text",
            "footer_order_link",
            "footer_channel_label",
            "footer_channel_text",
            "footer_channel_link",
        )
        widgets = {
            "brand_name": forms.TextInput(attrs={"class": "field"}),
            "meta_title": forms.TextInput(attrs={"class": "field"}),
            "hero_image": forms.ClearableFileInput(attrs={"class": "field"}),
            "hero_text": forms.Textarea(attrs={"rows": 4, "class": "field"}),
            "primary_cta_text": forms.TextInput(attrs={"class": "field"}),
            "primary_cta_link": forms.TextInput(attrs={"class": "field"}),
            "secondary_cta_text": forms.TextInput(attrs={"class": "field"}),
            "secondary_cta_link": forms.TextInput(attrs={"class": "field"}),
            "shop_title": forms.TextInput(attrs={"class": "field"}),
            "shop_subtitle": forms.TextInput(attrs={"class": "field"}),
            "inspiration_card_1": forms.TextInput(attrs={"class": "field"}),
            "inspiration_card_2": forms.TextInput(attrs={"class": "field"}),
            "inspiration_card_3": forms.TextInput(attrs={"class": "field"}),
            "inspiration_card_4": forms.TextInput(attrs={"class": "field"}),
            "inspiration_card_color": forms.TextInput({
                "class": "field",
                "placeholder": "HEX: #351321 یا RGB: rgb(53, 19, 33)",
                "dir": "ltr",
            }),
            "inspiration_text_color": forms.TextInput({
                "class": "field",
                "placeholder": "HEX: #f4e8df یا RGB: rgb(244, 232, 223)",
                "dir": "ltr",
            }),
            "inspiration_hatch": forms.CheckboxInput(),
            "track_title": forms.TextInput(attrs={"class": "field"}),
            "track_subtitle": forms.TextInput(attrs={"class": "field"}),
            "order_title": forms.TextInput(attrs={"class": "field"}),
            "order_subtitle": forms.TextInput(attrs={"class": "field"}),
            "footer_brand": forms.TextInput(attrs={"class": "field"}),
            "footer_text": forms.Textarea(attrs={"rows": 3, "class": "field"}),
            "footer_order_label": forms.TextInput(attrs={"class": "field"}),
            "telegram_order_id": forms.TextInput({
                "class": "field",
                "dir": "ltr",
                "placeholder": "مثال: my_telegram_username",
                "autocomplete": "off",
            }),
            "footer_order_text": forms.TextInput(attrs={"class": "field"}),
            "footer_order_link": forms.TextInput(attrs={"class": "field"}),
            "footer_channel_label": forms.TextInput(attrs={"class": "field"}),
            "footer_channel_text": forms.TextInput(attrs={"class": "field"}),
            "footer_channel_link": forms.TextInput(attrs={"class": "field"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["telegram_order_id"].help_text = (
            "فقط نام کاربری تلگرام را وارد کنید؛ برای نمونه @my_telegram_username. این شناسه مقصد سفارش سبد خرید است."
        )

    def clean_telegram_order_id(self):
        telegram_order_id = self.cleaned_data["telegram_order_id"].strip()
        if telegram_order_id.startswith("@"):
            telegram_order_id = telegram_order_id[1:]
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", telegram_order_id):
            raise ValidationError(
                "نام کاربری تلگرام باید ۵ تا ۳۲ حرف انگلیسی، عدد یا زیرخط باشد و با حرف شروع شود."
            )
        return telegram_order_id

class AdminCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username",)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user


class CustomerRegistrationForm(forms.Form):
    name = forms.CharField(
        label="نام و نام خانوادگی",
        max_length=120,
        widget=forms.TextInput(attrs={"class": "field", "autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="ایمیل",
        widget=forms.EmailInput(attrs={"class": "field", "autocomplete": "email", "dir": "ltr"}),
    )
    phone = forms.CharField(
        label="شماره موبایل",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "field", "autocomplete": "tel", "inputmode": "tel", "dir": "ltr"}),
    )
    password1 = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(attrs={"class": "field", "autocomplete": "new-password", "dir": "ltr"}),
    )
    password2 = forms.CharField(
        label="تکرار رمز عبور",
        widget=forms.PasswordInput(attrs={"class": "field", "autocomplete": "new-password", "dir": "ltr"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=email).exists() or user_model.objects.filter(username__iexact=email).exists():
            raise ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if len(phone) < 4 or not phone.lstrip("+").isdigit():
            raise ValidationError("شماره موبایل معتبر وارد کنید.")
        if CustomerProfile.objects.filter(phone=phone).exists():
            raise ValidationError("این شماره موبایل قبلاً ثبت شده است.")
        return phone

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "رمزهای عبور یکسان نیستند.")
        return cleaned_data

    def save(self):
        user = get_user_model().objects.create_user(
            username=self.cleaned_data["email"],
            email=self.cleaned_data["email"],
            first_name=self.cleaned_data["name"].strip(),
            password=self.cleaned_data["password1"],
        )
        CustomerProfile.objects.create(user=user, phone=self.cleaned_data["phone"])
        return user


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("customer_name", "phone", "address", "status")
        widgets = {
            "customer_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "phone": forms.TextInput(attrs={"inputmode": "tel", "dir": "ltr"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if len(phone) < 4 or not phone.lstrip("+").isdigit():
            raise ValidationError("شماره تلفن معتبر وارد کنید.")
        return phone


class OrderItemForm(forms.ModelForm):
    variant = forms.ModelChoiceField(
        label="سایز",
        queryset=ProductVariant.objects.select_related("product").order_by("product__name", "id"),
        required=False,
        empty_label="بدون سایز",
    )

    class Meta:
        model = OrderItem
        fields = ("product", "quantity", "unit_price")
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "unit_price": forms.NumberInput(attrs={"min": 0}),
        }

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        variant = cleaned_data.get("variant")
        if product and variant and variant.product_id != product.pk:
            self.add_error("variant", "سایز انتخاب‌شده متعلق به این محصول نیست.")
        if product and product.variants.exists() and not variant:
            self.add_error("variant", "برای این محصول باید سایز انتخاب کنید.")
        return cleaned_data

    def save(self, commit=True):
        item = super().save(commit=False)
        variant = self.cleaned_data.get("variant")
        item.variant_name = variant.size if variant else ""
        if commit:
            item.save()
        return item


OrderItemFormSetFactory = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
    max_num=50,
    validate_max=True,
)


def _category_slug(name):
    return slugify(name, allow_unicode=True)[:50].rstrip("-")


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(attrs={"autofocus": True}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if Category.objects.filter(name__iexact=name).exists():
            raise ValidationError("این دسته‌بندی از قبل ثبت شده است.")
        slug = _category_slug(name)
        if not slug:
            raise ValidationError("نام دسته‌بندی باید شامل حروف یا عدد باشد.")
        if Category.objects.filter(slug=slug).exists():
            raise ValidationError("برای این نام، شناسهٔ دسته‌بندی تکراری است.")
        return name

    def save(self, commit=True):
        category = super().save(commit=False)
        category.slug = _category_slug(category.name)
        if commit:
            category.save()
        return category


class ProductForm(forms.ModelForm):
    additional_images = MultipleImageField(
        label="تصاویر بیشتر محصول",
        required=False,
        widget=MultipleImageInput(attrs={"accept": "image/*"}),
    )
    discount_enabled = forms.BooleanField(label="اعمال تخفیف روی این محصول", required=False)
    discount_percent = forms.IntegerField(
        label="درصد تخفیف",
        required=False,
        min_value=1,
        max_value=90,
    )

    class Meta:
        model = Product
        fields = ("name", "category", "price", "stock", "image")
        widgets = {
            "price": forms.NumberInput(attrs={"min": 0}),
            "stock": forms.NumberInput(attrs={"min": 0}),
            "image": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            discounted = bool(self.instance.old_price and self.instance.old_price > self.instance.price)
            self.fields["price"].initial = self.instance.old_price if discounted else self.instance.price
            self.fields["discount_enabled"].initial = discounted
            if discounted:
                self.fields["discount_percent"].initial = round(
                    (self.instance.old_price - self.instance.price) * 100 / self.instance.old_price
                )
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("discount_enabled") and cleaned_data.get("discount_percent") is None:
            self.add_error("discount_percent", "درصد تخفیف را بین ۱ تا ۹۰ وارد کنید.")
        return cleaned_data

    def save(self, commit=True):
        product = super().save(commit=False)
        base_price = self.cleaned_data["price"]
        if self.cleaned_data.get("discount_enabled"):
            discount_percent = self.cleaned_data["discount_percent"]
            product.old_price = base_price
            product.price = (base_price * (100 - discount_percent) + 50) // 100
        else:
            product.old_price = None
            product.price = base_price
        if commit:
            product.save()
            self.save_m2m()
        return product


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ("size", "price")
        widgets = {
            "price": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.old_price and self.instance.old_price > self.instance.price:
            self.fields["price"].initial = self.instance.old_price


class ProductVariantFormSet(BaseInlineFormSet):
    def clean(self):
        if not any(self.errors):
            seen_sizes = set()
            for form in self.forms:
                if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                    continue
                size = form.cleaned_data.get("size", "").strip()
                normalized_size = size.casefold()
                if normalized_size in seen_sizes:
                    form.add_error("size", "این سایز برای محصول تکراری است.")
                seen_sizes.add(normalized_size)
        super().clean()

    def get_unique_error_message(self, unique_check):
        return "این سایز برای محصول تکراری است."


ProductVariantFormSetFactory = inlineformset_factory(
    Product,
    ProductVariant,
    form=ProductVariantForm,
    formset=ProductVariantFormSet,
    extra=1,
    can_delete=True,
)
