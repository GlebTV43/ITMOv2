from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from . import exchanges
from .forms import BookForm, MessageForm, OfferForm, ReadBookForm
from .models import Book, Exchange, ReadBook


def catalog(request):
    search = request.GET.get("q", "").strip()[:180]
    offer = request.GET.get("offer", "").strip()[:180]
    books = Book.objects.filter(status=Book.Status.AVAILABLE).select_related("owner")
    for word in search.casefold().split():
        books = books.filter(search_text__contains=word)
    for word in offer.casefold().split():
        books = books.filter(wanted_search__contains=word)
    page = Paginator(books, 18).get_page(request.GET.get("page"))
    return render(request, "books/catalog.html", {"page": page, "search": search, "offer": offer})


def book_detail(request, pk):
    book = get_object_or_404(Book.objects.select_related("owner"), pk=pk)
    related = Book.objects.filter(status=Book.Status.AVAILABLE).exclude(pk=book.pk)
    related = related.annotate(priority=Case(
        When(search_text=book.search_text, then=Value(0)),
        When(search_text__contains=book.author.casefold(), then=Value(1)),
        default=Value(2), output_field=IntegerField(),
    )).order_by("priority", "-created_at", "-pk")[:6]
    return render(request, "books/book.html", {"book": book, "related": related})


@login_required
@require_http_methods(["GET", "POST"])
def add_book(request):
    form = BookForm(request.POST, request.FILES) if request.method == "POST" else BookForm()
    if request.method == "POST" and form.is_valid():
        book = form.save(commit=False)
        book.owner = request.user
        book.save()
        return redirect("book", pk=book.pk)
    return render(request, "books/form.html", {
        "form": form, "heading": "Выставить книгу", "submit": "Опубликовать", "upload": True,
    })


def profile(request, pk):
    member = get_object_or_404(get_user_model(), pk=pk, is_active=True)
    listings = Book.objects.filter(owner=member).exclude(status=Book.Status.EXCHANGED)
    history = Exchange.objects.filter(exchanges.involving(member), status=Exchange.Status.COMPLETED)
    history = history.select_related("offered", "requested").order_by("-closed_at", "-pk")
    return render(request, "books/profile.html", {
        "member": member, "listings": listings, "history": history,
        "read_books": ReadBook.objects.filter(reader=member),
    })


@login_required
@require_http_methods(["GET", "POST"])
def add_read_book(request):
    form = ReadBookForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        book = form.save(commit=False)
        book.reader = request.user
        book.save()
        return redirect("profile", pk=request.user.pk)
    return render(request, "books/form.html", {
        "form": form, "heading": "Добавить прочитанную книгу", "submit": "Сохранить",
    })


@login_required
@require_http_methods(["GET", "POST"])
def propose(request, pk):
    book = get_object_or_404(Book.objects.exclude(owner=request.user), pk=pk)
    form = OfferForm(request.POST if request.method == "POST" else None, owner=request.user)
    if book.status != Book.Status.AVAILABLE:
        messages.error(request, "Книга уже недоступна для новых предложений.")
        return redirect("book", pk=pk)
    if request.method == "POST" and form.is_valid():
        try:
            exchange = exchanges.propose(
                request.user, form.cleaned_data["offered"].pk, pk, form.cleaned_data["text"],
            )
        except exchanges.ExchangeError as error:
            form.add_error(None, str(error))
        else:
            return redirect("exchange", pk=exchange.pk)
    return render(request, "books/form.html", {
        "form": form, "heading": f"Предложить обмен на «{book.title}»", "submit": "Отправить",
        "needs_book": not form.fields["offered"].queryset.exists(),
    })


@login_required
def exchange_list(request):
    items = Exchange.objects.filter(exchanges.involving(request.user)).select_related("offered", "requested")
    return render(request, "books/exchanges.html", {"exchanges": items})


@login_required
@require_http_methods(["GET", "POST"])
def exchange_detail(request, pk):
    exchange = get_object_or_404(
        Exchange.objects.select_related("offered__owner", "requested__owner"),
        exchanges.involving(request.user), pk=pk,
    )
    form = MessageForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            exchanges.send_message(pk, request.user, form.cleaned_data["text"])
        except exchanges.ExchangeError as error:
            messages.error(request, str(error))
        else:
            return redirect("exchange", pk=pk)
    return render(request, "books/exchange.html", {
        "exchange": exchange, "actions": exchanges.actions_for(exchange, request.user),
        "chat": exchange.messages.select_related("sender"), "form": form,
        "chat_open": exchange.status in ("pending", "accepted", "disputed"),
    })


@login_required
@require_POST
def exchange_action(request, pk, action):
    get_object_or_404(Exchange, exchanges.involving(request.user), pk=pk)
    try:
        exchanges.change_status(pk, request.user, action)
    except exchanges.ExchangeError as error:
        messages.error(request, str(error))
    return redirect("exchange", pk=pk)
