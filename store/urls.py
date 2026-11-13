from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"), path("checkout/", views.checkout, name="checkout"),
    path("checkout/submit/", views.checkout_submit, name="checkout_submit"),
    path("login/", views.login_view, name="login"),
    path("account/login/", views.customer_login, name="customer_login"),
    path("account/register/", views.customer_register, name="customer_register"),
    path("account/", views.customer_dashboard, name="customer_dashboard"),
    path("logout/", views.logout_view, name="logout"), path("panel/", views.dashboard, name="dashboard"),
    path("panel/password/", views.password_change, name="password_change"),
    path("panel/admins/", views.admin_manage, name="admin_manage"),
    path("panel/admins/<int:pk>/delete/", views.admin_delete, name="admin_delete"),
    path("panel/products/", views.product_list, name="product_list"),
    path("panel/categories/", views.category_list, name="category_list"),
    path("panel/faq/", views.faq_manage, name="faq_manage"),
    path("panel/products/new/", views.product_edit, name="product_add"),
    path("panel/products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("panel/products/<int:pk>/toggle/", views.product_toggle, name="product_toggle"),
    path("panel/products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("panel/orders/", views.order_list, name="order_list"),
    path("panel/orders/new/", views.order_add, name="order_add"),
    path("panel/site/", views.site_settings_edit, name="site_settings"),
    path("track/", views.track_order, name="track_order"),
    path("api/products/", views.products_api, name="products_api"),
]
