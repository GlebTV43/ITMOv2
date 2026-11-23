from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView
from django.core import signing
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import ActivateForm, EmailForm, LoginForm

User = get_user_model()
TOKEN_SALT = "bookshare.email-activation"


def limited(request, action, attempts, seconds):
    key = f"bookshare:{action}:{request.META.get('REMOTE_ADDR', 'local')}"
    cache.add(key, 0, seconds)
    try:
        return cache.incr(key) > attempts
    except ValueError:
        cache.add(key, 1, seconds)
        return False


class BookLoginView(LoginView):
    template_name = "books/form.html"
    authentication_form = LoginForm
    extra_context = {"heading": "Войти", "submit": "Войти", "is_login": True}

    def post(self, request, *args, **kwargs):
        if limited(request, "login", 20, 300):
            return HttpResponse("Слишком много попыток. Попробуйте через несколько минут.", status=429)
        return super().post(request, *args, **kwargs)


@require_http_methods(["GET", "POST"])
def register(request):
    form = EmailForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        if limited(request, "register", 10, 600):
            return HttpResponse("Слишком много запросов. Попробуйте позже.", status=429)
        email = form.cleaned_data["email"]
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                username=email, defaults={"email": email, "is_active": False},
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
        mail_key = f"bookshare:mail:{user.pk}"
        if not user.is_active and cache.add(mail_key, True, 60):
            token = signing.dumps(user.pk, salt=TOKEN_SALT)
            link = settings.PUBLIC_URL + reverse("activate", args=[token])
            try:
                send_mail(
                    "Подтвердите почту в «Дай почитать»",
                    f"Откройте ссылку, чтобы выбрать имя и пароль. Ссылка действует 24 часа.\n\n{link}",
                    None, [user.email],
                )
            except (SMTPException, OSError):
                cache.delete(mail_key)
                form.add_error(None, "Почтовый сервис временно недоступен. Попробуйте позже.")
                return render(request, "books/form.html", signup_context(form), status=503)
        messages.info(request, "Если адрес можно зарегистрировать, на него придёт ссылка для активации.")
        return redirect("login")
    return render(request, "books/form.html", signup_context(form))


def signup_context(form):
    return {"form": form, "heading": "Создать аккаунт", "submit": "Отправить ссылку",
            "description": "После подтверждения почты вы сможете задать имя и пароль."}


@never_cache
@require_http_methods(["GET", "POST"])
def activate(request, token):
    try:
        user_id = signing.loads(token, salt=TOKEN_SALT, max_age=86400)
    except signing.BadSignature:
        user_id = None
    user = User.objects.filter(pk=user_id, is_active=False).first() if user_id else None
    if not user:
        return render(request, "books/activation_invalid.html", status=400)
    form = ActivateForm(user, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        updated = User.objects.filter(pk=user.pk, is_active=False).update(
            first_name=form.cleaned_data["name"], password=user.password, is_active=True,
        )
        if updated:
            messages.success(request, "Почта подтверждена. Войдите с новым паролем.")
            return redirect("login")
        return render(request, "books/activation_invalid.html", status=400)
    return render(request, "books/form.html", {
        "form": form, "heading": "Подтвердить почту", "submit": "Активировать аккаунт",
    })
