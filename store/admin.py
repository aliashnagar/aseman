from django.contrib import admin
from .forms import ProductVariantFormSet
from .models import Category, CustomerProfile, FAQ, Order, OrderItem, Product, ProductVariant


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "position")
    ordering = ("position", "id")


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone")
    search_fields = ("user__email", "user__first_name", "phone")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    formset = ProductVariantFormSet
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)
    inlines = [ProductVariantInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("unit_price",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "phone", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("customer_name", "phone")
    inlines = [OrderItemInline]
