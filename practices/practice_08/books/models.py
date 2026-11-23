from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import F, Q


def book_photo_path(instance, filename):
    return f"covers/{uuid4().hex}.jpg"


class Book(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Доступна"
        RESERVED = "reserved", "Зарезервирована"
        EXCHANGED = "exchanged", "Передана"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    title = models.CharField("Название", max_length=180)
    author = models.CharField("Автор", max_length=140)
    photo = models.ImageField("Фото состояния", upload_to=book_photo_path)
    description = models.TextField("Описание и состояние", max_length=2000)
    wanted = models.TextField("На какие книги обменяю", max_length=1000)
    search_text = models.TextField(editable=False)
    wanted_search = models.TextField(editable=False)
    status = models.CharField(max_length=12, choices=Status, default=Status.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def save(self, **kwargs):
        self.search_text = f"{self.title}\n{self.author}".casefold()
        self.wanted_search = self.wanted.casefold()
        super().save(**kwargs)

    def __str__(self):
        return self.title


class ReadBook(models.Model):
    reader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField("Название", max_length=180)
    author = models.CharField("Автор", max_length=140)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added_at", "-pk"]


class Exchange(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На рассмотрении"
        ACCEPTED = "accepted", "Согласован"
        DECLINED = "declined", "Отклонён"
        CANCELLED = "cancelled", "Отменён"
        COMPLETED = "completed", "Завершён"
        DISPUTED = "disputed", "Спор"

    offered = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="offers_made")
    requested = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="offers_received")
    status = models.CharField(max_length=12, choices=Status, default=Status.PENDING)
    proposer_received = models.DateTimeField(null=True, blank=True)
    recipient_received = models.DateTimeField(null=True, blank=True)
    cancel_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=~Q(offered=F("requested")), name="two_distinct_books"),
            models.UniqueConstraint(
                fields=["offered", "requested"], condition=Q(status="pending"),
                name="one_pending_offer_per_pair",
            ),
        ]


class Message(models.Model):
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    text = models.TextField("Сообщение", max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
