from io import BytesIO
from pathlib import Path
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Category, CustomerProfile, Order, OrderItem, Product, ProductVariant, SiteSettings, SocialLink
from .forms import CustomerRegistrationForm, SiteSettingsForm


class ProductVariantTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.user = get_user_model().objects.create_user(username="manager", password="test-password")
        self.category = Category.objects.create(name="تابلو", slug="تابلو")
        self.client.force_login(self.user)

    def product_data(self, **overrides):
        data = {
            "name": "تابلو ماه",
            "category": self.category.pk,
            "price": "100000",
            "stock": "5",
            "discount_enabled": "on",
            "discount_percent": "10",
            "variants-TOTAL_FORMS": "2",
            "variants-INITIAL_FORMS": "0",
            "variants-MIN_NUM_FORMS": "0",
            "variants-MAX_NUM_FORMS": "1000",
            "variants-0-size": "کوچک",
            "variants-0-price": "80000",
            "variants-1-size": "بزرگ",
            "variants-1-price": "120000",
        }
        data.update(overrides)
        return data

    def image_upload(self, name):
        image_bytes = BytesIO()
        Image.new("RGB", (2, 2), color="white").save(image_bytes, format="PNG")
        return SimpleUploadedFile(name, image_bytes.getvalue(), content_type="image/png")

    def test_product_gallery_images_upload_and_appear_in_product_api(self):
        response = self.client.post(
            reverse("product_add"),
            self.product_data(
                image=self.image_upload("main.png"),
                additional_images=[
                    self.image_upload("gallery-one.png"),
                    self.image_upload("gallery-two.png"),
                ],
            ),
        )

        self.assertRedirects(response, reverse("product_list"))
        product = Product.objects.get(name="تابلو ماه")
        self.assertEqual(product.gallery_images.count(), 2)
        api_response = self.client.get(reverse("products_api"))
        product_data = api_response.json()["products"][0]
        self.assertEqual(len(product_data["gallery_images"]), 2)
        self.assertTrue(product_data["image_url"].endswith("/main.png"))

    def test_product_gallery_images_can_be_removed_in_product_editor(self):
        product = Product.objects.create(
            name="تابلو ماه",
            category=self.category,
            price=100000,
            stock=5,
        )
        gallery_image = product.gallery_images.create(image=self.image_upload("gallery.png"))
        image_path = Path(gallery_image.image.path)

        response = self.client.post(
            reverse("product_edit", args=[product.pk]),
            self.product_data(
                name=product.name,
                additional_images=[],
                remove_images=[str(gallery_image.pk)],
                **{
                    "variants-0-size": "",
                    "variants-0-price": "",
                    "variants-1-size": "",
                    "variants-1-price": "",
                },
            ),
        )

        self.assertRedirects(response, reverse("product_list"))
        self.assertFalse(product.gallery_images.exists())
        self.assertFalse(image_path.exists())

    def test_deleting_product_removes_its_gallery_files(self):
        product = Product.objects.create(
            name="تابلو ماه",
            category=self.category,
            price=100000,
            stock=5,
        )
        gallery_image = product.gallery_images.create(image=self.image_upload("gallery.png"))
        image_path = Path(gallery_image.image.path)

        response = self.client.post(reverse("product_delete", args=[product.pk]))

        self.assertRedirects(response, reverse("product_list"))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertFalse(image_path.exists())

    def test_saves_and_exposes_individually_priced_sizes(self):
        response = self.client.post(reverse("product_add"), self.product_data())

        self.assertRedirects(response, reverse("product_list"))
        product = Product.objects.get(name="تابلو ماه")
        self.assertEqual(
            list(product.variants.order_by("size").values_list("size", "price", "old_price")),
            [("بزرگ", 108000, 120000), ("کوچک", 72000, 80000)],
        )

        api_response = self.client.get(reverse("products_api"))
        self.assertEqual(api_response.status_code, 200)
        variants = api_response.json()["products"][0]["variants"]
        self.assertEqual({variant["size"]: variant["price"] for variant in variants}, {
            "کوچک": 72000,
            "بزرگ": 108000,
        })

    def test_rejects_duplicate_size_labels(self):
        data = self.product_data(**{
            "variants-1-size": " کوچک ",
            "variants-1-price": "90000",
        })

        response = self.client.post(reverse("product_add"), data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.exists())
        self.assertContains(response, "این سایز برای محصول تکراری است.")

    def test_product_without_sizes_keeps_legacy_price(self):
        data = self.product_data(**{
            "variants-0-size": "",
            "variants-0-price": "",
            "variants-1-size": "",
            "variants-1-price": "",
        })

        response = self.client.post(reverse("product_add"), data)

        self.assertRedirects(response, reverse("product_list"))
        product = Product.objects.get(name="تابلو ماه")
        self.assertEqual(product.price, 90000)
        self.assertFalse(ProductVariant.objects.filter(product=product).exists())

    def test_products_api_includes_non_cancelled_sold_quantities(self):
        popular = Product.objects.create(
            name="پرفروش",
            category=self.category,
            price=100000,
            stock=5,
        )
        less_popular = Product.objects.create(
            name="کم‌فروش",
            category=self.category,
            price=100000,
            stock=5,
        )
        popular_order = Order.objects.create(
            customer_name="مشتری",
            phone="09120000000",
            address="نشانی",
        )
        OrderItem.objects.create(
            order=popular_order,
            product=popular,
            quantity=4,
            unit_price=100000,
        )
        cancelled_order = Order.objects.create(
            customer_name="مشتری",
            phone="09120000000",
            address="نشانی",
            status=Order.Status.CANCELLED,
        )
        OrderItem.objects.create(
            order=cancelled_order,
            product=popular,
            quantity=10,
            unit_price=100000,
        )
        less_popular_order = Order.objects.create(
            customer_name="مشتری",
            phone="09120000000",
            address="نشانی",
        )
        OrderItem.objects.create(
            order=less_popular_order,
            product=less_popular,
            quantity=2,
            unit_price=100000,
        )

        response = self.client.get(reverse("products_api"))

        sold_quantities = {
            product["name"]: product["sold_quantity"]
            for product in response.json()["products"]
        }
        self.assertEqual(sold_quantities, {"پرفروش": 4, "کم‌فروش": 2})

    def test_header_contains_search_without_category_chips(self):
        response = self.client.get(reverse("home"), {"q": "ماه"})

        self.assertContains(response, 'id="q"')
        self.assertContains(response, 'value="ماه"')
        self.assertNotContains(response, "data-category")

    def test_product_management_renders_variant_price_range(self):
        product = Product.objects.create(
            name="تابلو ماه",
            category=self.category,
            price=100000,
            stock=5,
        )
        ProductVariant.objects.create(product=product, size="کوچک", price=72000)
        ProductVariant.objects.create(product=product, size="بزرگ", price=108000)

        response = self.client.get(reverse("product_list"))

        self.assertContains(response, "قیمت بر اساس سایز")
        self.assertContains(response, "72000 تا 108000 تومان")

    def test_product_management_searches_by_name_or_category(self):
        matching = Product.objects.create(
            name="تابلو ماه",
            category=self.category,
            price=100000,
        )
        Product.objects.create(
            name="گل مخملی",
            category=Category.objects.create(name="گل", slug="گل"),
            price=20000,
        )

        response = self.client.get(reverse("product_list"), {"q": "تابلو"})

        self.assertContains(response, matching.name)
        self.assertNotContains(response, "گل مخملی")
        self.assertContains(response, 'value="تابلو"')


class AdminAccountTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="root",
            password="Root-Strong-Password-839!",
        )
        self.client.force_login(self.user)

    def settings_data(self, site):
        data = {
            name: getattr(site, name)
            for name in SiteSettingsForm.Meta.fields
            if name != "hero_image"
        }
        data.update({
            "footer_socials-TOTAL_FORMS": "0",
            "footer_socials-INITIAL_FORMS": "0",
            "footer_socials-MIN_NUM_FORMS": "0",
            "footer_socials-MAX_NUM_FORMS": "20",
        })
        return data

    def test_primary_admin_pages_render_account_controls(self):
        admins = self.client.get(reverse("admin_manage"))
        password = self.client.get(reverse("password_change"))
        site_settings = self.client.get(reverse("site_settings"))

        self.assertContains(admins, "ساخت حساب ادمین")
        self.assertContains(admins, 'id="panel-menu"')
        self.assertContains(admins, "panel-menu-toggle")
        self.assertContains(password, "تغییر رمز عبور")
        self.assertContains(site_settings, "عنوان و تصویر اصلی")
        self.assertContains(site_settings, "دکمه‌های صفحه اصلی")
        self.assertContains(site_settings, "فوتر و راه‌های ارتباطی")
        self.assertContains(site_settings, "کارت‌های الهام‌بخش")
        self.assertContains(site_settings, "رنگ نوشته کارت‌ها")
        self.assertContains(site_settings, 'data-color-picker-for="id_inspiration_card_color"')
        self.assertContains(site_settings, 'data-color-picker-for="id_inspiration_text_color"')
        self.assertContains(site_settings, 'id="add-footer-social"')
        self.assertContains(site_settings, "توضیح زیر نام سایت در فوتر")

    def test_primary_admin_can_customize_inspiration_cards(self):
        site = SiteSettings.get()
        data = self.settings_data(site)
        data.update({
            "inspiration_card_1": "A little joy, made for you.",
            "inspiration_card_color": "#123456",
            "inspiration_text_color": "#abcdef",
        })
        data.pop("inspiration_hatch")

        response = self.client.post(reverse("site_settings"), data)

        self.assertRedirects(response, reverse("site_settings"))
        site.refresh_from_db()
        self.assertEqual(site.inspiration_card_1, "A little joy, made for you.")
        self.assertEqual(site.inspiration_card_color, "#123456")
        self.assertEqual(site.inspiration_text_color, "#abcdef")
        self.assertFalse(site.inspiration_hatch)
        home = self.client.get(reverse("home"))
        self.assertContains(home, "A little joy, made for you.")
        self.assertContains(home, "--inspiration-card-color: #123456")
        self.assertContains(home, "--inspiration-text-color: #abcdef")
        self.assertNotContains(home, "inspiration-card--hatched")

    def test_primary_admin_can_save_order_username_and_links_independently(self):
        site = SiteSettings.get()
        data = self.settings_data(site)
        data["telegram_order_id"] = "@new_order_account"
        data["secondary_cta_link"] = "https://t.me/cta_order_account"
        data["footer_order_link"] = "https://t.me/footer_order_account"
        data["footer_order_text"] = "@footer_order_account"
        data["footer_text"] = "توضیح تازهٔ برند در فوتر"

        response = self.client.post(reverse("site_settings"), data)

        self.assertRedirects(response, reverse("site_settings"))
        site.refresh_from_db()
        self.assertEqual(site.telegram_order_id, "new_order_account")
        self.assertEqual(site.secondary_cta_link, "https://t.me/cta_order_account")
        self.assertEqual(site.footer_order_link, "https://t.me/footer_order_account")
        self.assertEqual(site.footer_order_text, "@footer_order_account")
        self.assertEqual(site.footer_text, "توضیح تازهٔ برند در فوتر")
        home = self.client.get(reverse("home"))
        checkout = self.client.get(reverse("checkout"))
        self.assertContains(checkout, 'data-telegram-order-id="new_order_account"')
        self.assertContains(home, 'href="https://t.me/cta_order_account"')
        self.assertContains(home, 'href="https://t.me/footer_order_account"')
        self.assertContains(home, "@footer_order_account")
        self.assertContains(home, "توضیح تازهٔ برند در فوتر")

    def test_primary_admin_can_add_edit_and_delete_footer_social_links(self):
        site = SiteSettings.get()
        data = self.settings_data(site)
        data.update({
            "footer_socials-TOTAL_FORMS": "1",
            "footer_socials-0-label": "اینستاگرام",
            "footer_socials-0-icon": SocialLink.Icon.INSTAGRAM,
            "footer_socials-0-url": "https://instagram.com/aseman",
        })

        response = self.client.post(reverse("site_settings"), data)

        self.assertRedirects(response, reverse("site_settings"))
        social = site.social_links.get()
        self.assertEqual((social.label, social.icon, social.url), (
            "اینستاگرام",
            SocialLink.Icon.INSTAGRAM,
            "https://instagram.com/aseman",
        ))
        self.assertContains(self.client.get(reverse("home")), 'aria-label="اینستاگرام"')

        data = self.settings_data(site)
        data.update({
            "footer_socials-TOTAL_FORMS": "1",
            "footer_socials-INITIAL_FORMS": "1",
            "footer_socials-0-id": str(social.pk),
            "footer_socials-0-label": "اینستاگرام فروشگاه",
            "footer_socials-0-icon": SocialLink.Icon.INSTAGRAM,
            "footer_socials-0-url": "https://instagram.com/aseman_shop",
        })
        response = self.client.post(reverse("site_settings"), data)

        self.assertRedirects(response, reverse("site_settings"))
        social.refresh_from_db()
        self.assertEqual(social.label, "اینستاگرام فروشگاه")
        self.assertEqual(social.url, "https://instagram.com/aseman_shop")
        self.assertContains(self.client.get(reverse("home")), 'href="https://instagram.com/aseman_shop"')

        data = self.settings_data(site)
        data.update({
            "footer_socials-TOTAL_FORMS": "1",
            "footer_socials-INITIAL_FORMS": "1",
            "footer_socials-0-id": str(social.pk),
            "footer_socials-0-label": social.label,
            "footer_socials-0-icon": social.icon,
            "footer_socials-0-url": social.url,
            "footer_socials-0-DELETE": "on",
        })
        response = self.client.post(reverse("site_settings"), data)

        self.assertRedirects(response, reverse("site_settings"))
        self.assertFalse(site.social_links.exists())
        self.assertNotContains(self.client.get(reverse("home")), 'href="https://instagram.com/aseman_shop"')

    def test_primary_admin_cannot_save_invalid_telegram_order_username(self):
        site = SiteSettings.get()
        data = self.settings_data(site)
        data["telegram_order_id"] = "not a valid username"

        response = self.client.post(reverse("site_settings"), data)

        self.assertEqual(response.status_code, 200)
        site.refresh_from_db()
        self.assertEqual(site.telegram_order_id, "tablo_aseman_shab")
        self.assertContains(response, "نام کاربری تلگرام باید")

    def test_inspiration_colors_accept_rgb_values(self):
        site = SiteSettings.get()
        data = self.settings_data(site)
        data.update({
            "inspiration_card_color": "rgb(53, 19, 33)",
            "inspiration_text_color": "RGB(244, 232, 223)",
        })

        response = self.client.post(reverse("site_settings"), data)

        self.assertRedirects(response, reverse("site_settings"))
        site.refresh_from_db()
        self.assertEqual(site.inspiration_card_color, "rgb(53, 19, 33)")
        self.assertEqual(site.inspiration_text_color, "RGB(244, 232, 223)")

    def test_inspiration_colors_reject_invalid_values(self):
        site = SiteSettings.get()
        data = self.settings_data(site)
        data["inspiration_card_color"] = "red; background:url(javascript:alert(1))"

        response = self.client.post(reverse("site_settings"), data)

        self.assertEqual(response.status_code, 200)
        site.refresh_from_db()
        self.assertEqual(site.inspiration_card_color, "#351321")

    def test_primary_admin_can_create_secondary_admin(self):
        response = self.client.post(reverse("admin_manage"), {
            "username": "assistant",
            "password1": "Assistant-Strong-Password-928!",
            "password2": "Assistant-Strong-Password-928!",
        })

        self.assertRedirects(response, reverse("admin_manage"))
        assistant = get_user_model().objects.get(username="assistant")
        self.assertTrue(assistant.check_password("Assistant-Strong-Password-928!"))
        self.assertFalse(assistant.is_superuser)
        self.assertFalse(assistant.is_staff)

    def test_primary_admin_can_delete_secondary_admin(self):
        assistant = get_user_model().objects.create_user(
            username="assistant",
            password="Assistant-Strong-Password-928!",
        )

        response = self.client.post(reverse("admin_delete", args=[assistant.pk]))

        self.assertRedirects(response, reverse("admin_manage"))
        self.assertFalse(get_user_model().objects.filter(pk=assistant.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_primary_admin_cannot_delete_superuser(self):
        response = self.client.post(reverse("admin_delete", args=[self.user.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_secondary_admin_cannot_delete_accounts(self):
        assistant = get_user_model().objects.create_user(
            username="assistant",
            password="Assistant-Strong-Password-928!",
        )
        self.client.force_login(assistant)
        another = get_user_model().objects.create_user(
            username="another",
            password="Another-Strong-Password-928!",
        )

        response = self.client.post(reverse("admin_delete", args=[another.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(get_user_model().objects.filter(pk=another.pk).exists())

    def test_secondary_admin_cannot_create_another_admin(self):
        assistant = get_user_model().objects.create_user(
            username="assistant",
            password="Assistant-Strong-Password-928!",
        )
        self.client.force_login(assistant)

        response = self.client.get(reverse("admin_manage"))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_change_password_without_losing_session(self):
        self.client.post(reverse("password_change"), {
            "old_password": "Root-Strong-Password-839!",
            "new_password1": "Changed-Strong-Password-847!",
            "new_password2": "Changed-Strong-Password-847!",
        })

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Changed-Strong-Password-847!"))
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_secondary_admin_can_change_own_password(self):
        assistant = get_user_model().objects.create_user(
            username="assistant",
            password="Assistant-Strong-Password-928!",
        )
        self.client.force_login(assistant)

        response = self.client.post(reverse("password_change"), {
            "old_password": "Assistant-Strong-Password-928!",
            "new_password1": "Assistant-Changed-Password-947!",
            "new_password2": "Assistant-Changed-Password-947!",
        })

        self.assertRedirects(response, reverse("password_change"))
        assistant.refresh_from_db()
        self.assertTrue(assistant.check_password("Assistant-Changed-Password-947!"))


class CustomerAccountTests(TestCase):
    def register(self, **overrides):
        data = {
            "name": "مریم رضایی",
            "email": "maryam@example.com",
            "phone": "۰۹۱۲ ۳۴۵ ۶۷۸۹",
            "password1": "Customer-Strong-Password-847!",
            "password2": "Customer-Strong-Password-847!",
        }
        data.update(overrides)
        return self.client.post(reverse("customer_register"), data)

    def test_registration_creates_customer_and_logs_in(self):
        response = self.register()

        self.assertRedirects(response, reverse("customer_dashboard"))
        user = get_user_model().objects.get(email="maryam@example.com")
        self.assertTrue(user.check_password("Customer-Strong-Password-847!"))
        self.assertEqual(user.customer_profile.phone, "09123456789")
        self.assertContains(self.client.get(reverse("customer_dashboard")), "مریم رضایی عزیز خوش آمدی")

    def test_customer_login_and_registration_are_separate_pages(self):
        login_page = self.client.get(reverse("customer_login"))
        register_page = self.client.get(reverse("customer_register"))

        self.assertContains(login_page, "حساب کاربری ندارید؟ ثبت‌نام کنید")
        self.assertNotContains(login_page, "تکرار رمز عبور")
        self.assertContains(register_page, "ثبت‌نام مشتریان")
        self.assertContains(register_page, "تکرار رمز عبور")
        self.assertContains(register_page, "حساب کاربری دارید؟ وارد شوید")

    def test_invalid_registration_stays_on_registration_page_with_errors(self):
        response = self.client.post(reverse("customer_register"), {
            "name": "مریم رضایی",
            "email": "invalid",
            "phone": "09123456789",
            "password1": "Customer-Strong-Password-847!",
            "password2": "Customer-Strong-Password-847!",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ثبت‌نام مشتریان")
        self.assertContains(response, "یک ایمیل آدرس معتبر وارد کنید.")

    def test_customer_dashboard_redirects_guests_to_customer_login(self):
        response = self.client.get(reverse("customer_dashboard"))

        self.assertRedirects(response, f"{reverse('customer_login')}?next={reverse('customer_dashboard')}")

    def test_registration_rejects_duplicate_email_and_phone(self):
        self.register()

        duplicate_email = CustomerRegistrationForm({
            "name": "مشتری دیگر",
            "email": "MARYAM@example.com",
            "phone": "09121111111",
            "password1": "Another-Strong-Password-847!",
            "password2": "Another-Strong-Password-847!",
        })
        duplicate_phone = CustomerRegistrationForm({
            "name": "مشتری دیگر",
            "email": "another@example.com",
            "phone": "۰۹۱۲۳۴۵۶۷۸۹",
            "password1": "Another-Strong-Password-847!",
            "password2": "Another-Strong-Password-847!",
        })

        self.assertFalse(duplicate_email.is_valid())
        self.assertIn("email", duplicate_email.errors)
        self.assertFalse(duplicate_phone.is_valid())
        self.assertIn("phone", duplicate_phone.errors)

    def test_customer_can_login_with_email_or_phone(self):
        self.register()
        self.client.logout()

        email_response = self.client.post(reverse("customer_login"), {
            "action": "login",
            "identifier": "MARYAM@example.com",
            "password": "Customer-Strong-Password-847!",
        })
        self.assertRedirects(email_response, reverse("customer_dashboard"))
        self.client.logout()
        phone_response = self.client.post(reverse("customer_login"), {
            "action": "login",
            "identifier": "۰۹۱۲۳۴۵۶۷۸۹",
            "password": "Customer-Strong-Password-847!",
        })

        self.assertRedirects(phone_response, reverse("customer_dashboard"))

    def test_customer_dashboard_shows_only_orders_for_account_phone(self):
        self.register()
        customer_order = Order.objects.create(
            customer_name="مریم رضایی",
            phone="09123456789",
            address="تهران",
        )
        other_order = Order.objects.create(
            customer_name="مشتری دیگر",
            phone="09120000000",
            address="شیراز",
        )

        response = self.client.get(reverse("customer_dashboard"))

        self.assertContains(response, f"#{customer_order.pk}")
        self.assertNotContains(response, f"#{other_order.pk}")
        self.assertContains(response, "تغییر رمز عبور")
        self.assertContains(response, "علاقه‌مندی‌های من")

    def test_customer_cannot_open_management_pages(self):
        self.register()

        for page in ("dashboard", "product_list", "order_list", "password_change"):
            with self.subTest(page=page):
                self.assertEqual(self.client.get(reverse(page)).status_code, 403)

    def test_customer_can_change_password_without_losing_session(self):
        self.register()

        response = self.client.post(reverse("customer_dashboard"), {
            "action": "password_change",
            "old_password": "Customer-Strong-Password-847!",
            "new_password1": "Customer-Changed-Password-947!",
            "new_password2": "Customer-Changed-Password-947!",
        })

        self.assertRedirects(response, reverse("customer_dashboard"))
        user = get_user_model().objects.get(email="maryam@example.com")
        self.assertTrue(user.check_password("Customer-Changed-Password-947!"))
        self.assertEqual(self.client.get(reverse("customer_dashboard")).status_code, 200)

    def test_homepage_account_icon_links_to_customer_login(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, reverse("customer_login"))
        self.assertNotContains(response, 'id="wl"')
        self.assertContains(response, 'id="category-filter"')
        self.assertContains(response, 'id="so"')
        self.assertNotContains(response, 'id="favorites-toggle"')
        self.assertContains(response, "تکمیل سفارش")

    def test_homepage_categories_are_available_as_shop_filters(self):
        category = Category.objects.create(name="چراغ خواب", slug="چراغ-خواب")
        Product.objects.create(name="چراغ ماه", category=category, price=80000)
        inactive_category = Category.objects.create(name="قدیمی", slug="قدیمی")
        Product.objects.create(
            name="محصول غیرفعال",
            category=inactive_category,
            price=50000,
            is_active=False,
        )

        response = self.client.get(reverse("home"), {"category": category.slug})

        self.assertContains(response, 'value="چراغ-خواب" selected')
        self.assertContains(response, "چراغ خواب")
        self.assertNotContains(response, "محصول غیرفعال")
        self.assertContains(response, 'aria-label="دسته‌بندی‌های فروشگاه"')
        self.assertContains(response, "دسترسی سریع")
        self.assertContains(response, "شبکه‌های اجتماعی")


class ManualOrderTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="manager", password="test-password")
        self.client.force_login(user)
        self.category = Category.objects.create(name="تابلو", slug="تابلو")
        self.product = Product.objects.create(
            name="تابلو ماه",
            category=self.category,
            price=100000,
            stock=5,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size="بزرگ",
            price=150000,
        )

    def test_manual_order_form_lists_products_and_sizes_for_price_selection(self):
        response = self.client.get(reverse("order_add"))

        self.assertContains(response, "ثبت سفارش تلگرامی")
        self.assertContains(response, "order-products-data")
        self.assertContains(response, "تابلو ماه")

    def test_manual_order_has_tracking_number_and_phone_lookup(self):
        response = self.client.post(reverse("order_add"), {
            "customer_name": "مشتری",
            "phone": "۰۹۱۲۳۴۵۶۷۸۹",
            "address": "تهران، خیابان نمونه",
            "status": Order.Status.NEW,
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "50",
            "items-0-product": str(self.product.pk),
            "items-0-variant": str(self.variant.pk),
            "items-0-quantity": "2",
            "items-0-unit_price": "150000",
        })

        self.assertRedirects(response, reverse("order_list"))
        order = Order.objects.get(phone="09123456789")
        item = OrderItem.objects.get(order=order)
        self.assertEqual((item.variant_name, item.quantity, item.unit_price), ("بزرگ", 2, 150000))

        tracking = self.client.post(reverse("track_order"), {
            "number": str(order.pk),
            "phone": "6789",
        })
        self.assertContains(tracking, "تابلو ماه (بزرگ) × 2")

    def test_manual_order_rejects_variant_belonging_to_another_product(self):
        another_product = Product.objects.create(
            name="محصول دیگر",
            category=self.category,
            price=20000,
        )

        response = self.client.post(reverse("order_add"), {
            "customer_name": "مشتری",
            "phone": "09123456789",
            "address": "تهران، خیابان نمونه",
            "status": Order.Status.NEW,
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-MAX_NUM_FORMS": "50",
            "items-0-product": str(another_product.pk),
            "items-0-variant": str(self.variant.pk),
            "items-0-quantity": "1",
            "items-0-unit_price": "20000",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())


class CheckoutPageTests(TestCase):
    def test_static_css_uses_absolute_url_on_home_and_checkout(self):
        home = self.client.get(reverse("home"))
        checkout = self.client.get(reverse("checkout"))

        self.assertContains(home, 'href="/static/store/css/site.css?v=36"')
        self.assertContains(checkout, 'href="/static/store/css/site.css?v=36"')

    def test_checkout_page_has_shipping_details_and_payment_options(self):
        response = self.client.get(reverse("checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "نام و نام خانوادگی")
        self.assertContains(response, "استان")
        self.assertContains(response, "شهر")
        self.assertContains(response, "آدرس کامل")
        self.assertContains(response, "کد پستی")
        self.assertContains(response, "از طریق درگاه پرداخت")
        self.assertContains(response, "از طریق کارت‌به‌کارت")
        self.assertContains(response, "ثبت سفارش از طریق تلگرام")
        self.assertContains(response, 'value="gateway"')
        self.assertContains(response, 'value="card_transfer"')
