from django.urls import path

from . import views

urlpatterns = [
    #path("hello-names/", views.say_hello_to_user),
    path("search-catalog/", views.search_book_catalog, name='catalog'),
    path("trending/", views.trending, name="trending"),
    path("recommendations/", views.personal_rec, name="rec"),
    path("addToCart", views.addToCart, name="addToCart"),
    path("remFromCart", views.remFromCart, name="remFromCart"),
    path('generate_coupons/', views.analytics_coupon_creation, name='generate_coupons'),
    path("create-user", views.create_user_form, name='create_user'),
    path("login-user/", views.login_form, name='login_user'),
]