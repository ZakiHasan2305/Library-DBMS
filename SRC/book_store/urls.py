from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    #gets all functions from book_store_app's url.py
    path('', include("book_store_app.urls")),
]