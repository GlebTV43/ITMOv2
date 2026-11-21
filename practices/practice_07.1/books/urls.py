from django.contrib.auth.views import LogoutView
from django.urls import path

from . import accounts, views

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("register/", accounts.register, name="register"),
    path("activate/<str:token>/", accounts.activate, name="activate"),
    path("login/", accounts.BookLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("books/new/", views.add_book, name="add_book"),
    path("books/<int:pk>/", views.book_detail, name="book"),
    path("books/<int:pk>/offer/", views.propose, name="propose"),
    path("people/<int:pk>/", views.profile, name="profile"),
    path("reading/new/", views.add_read_book, name="add_read_book"),
    path("exchanges/", views.exchange_list, name="exchanges"),
    path("exchanges/<int:pk>/", views.exchange_detail, name="exchange"),
    path("exchanges/<int:pk>/<str:action>/", views.exchange_action, name="exchange_action"),
]
