from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Book, Exchange, Message

STATUS = Exchange.Status


class ExchangeError(Exception):
    pass


def involving(user):
    return Q(offered__owner=user) | Q(requested__owner=user)


def book_pair(exchange):
    return Book.objects.filter(pk__in=[exchange.offered_id, exchange.requested_id])


@transaction.atomic
def propose(actor, offered_id, requested_id, text):
    available = Book.objects.filter(status=Book.Status.AVAILABLE)
    offered = available.filter(pk=offered_id, owner=actor).first()
    requested = available.filter(pk=requested_id).exclude(owner=actor).first()
    if not offered or not requested:
        raise ExchangeError("Одна из книг уже недоступна.")
    exchange, created = Exchange.objects.get_or_create(
        offered=offered, requested=requested, status=STATUS.PENDING,
    )
    if not created:
        raise ExchangeError("У вас уже есть открытое предложение для этой пары книг.")
    Message.objects.create(exchange=exchange, sender=actor, text=text)
    return exchange


def close(exchange, status):
    exchange.status = status
    exchange.closed_at = timezone.now()
    exchange.cancel_requested_by = None


def accept(exchange):
    books = book_pair(exchange)
    if books.filter(status=Book.Status.AVAILABLE).update(status=Book.Status.RESERVED) != 2:
        raise ExchangeError("Одна из книг уже участвует в другом обмене.")
    other_offers = Exchange.objects.filter(status=STATUS.PENDING).exclude(pk=exchange.pk)
    book_ids = (exchange.offered_id, exchange.requested_id)
    closed_at = timezone.now()
    other_offers.filter(offered_id__in=book_ids).update(status=STATUS.CANCELLED, closed_at=closed_at)
    other_offers.filter(requested_id__in=book_ids).update(status=STATUS.CANCELLED, closed_at=closed_at)
    exchange.status = STATUS.ACCEPTED


def mark_received(exchange, actor):
    stamp = timezone.now()
    if actor.pk == exchange.offered.owner_id:
        exchange.proposer_received = exchange.proposer_received or stamp
    else:
        exchange.recipient_received = exchange.recipient_received or stamp
    exchange.cancel_requested_by = None
    if exchange.proposer_received and exchange.recipient_received:
        close(exchange, STATUS.COMPLETED)
        book_pair(exchange).update(status=Book.Status.EXCHANGED)


def actions_for(exchange, actor):
    proposer = actor.pk == exchange.offered.owner_id
    if exchange.status == STATUS.PENDING:
        return {"withdraw": "Отозвать предложение"} if proposer else {
            "accept": "Принять предложение", "decline": "Отклонить",
        }
    if exchange.status not in (STATUS.ACCEPTED, STATUS.DISPUTED):
        return {}
    actions = {}
    received = exchange.proposer_received if proposer else exchange.recipient_received
    if not received:
        actions["received"] = "Подтверждаю получение"
    if exchange.status == STATUS.ACCEPTED:
        actions["dispute"] = "Открыть спор"
    if not exchange.proposer_received and not exchange.recipient_received:
        if not exchange.cancel_requested_by_id:
            actions["cancel"] = "Предложить отмену"
        elif exchange.cancel_requested_by_id != actor.pk:
            actions["cancel"] = "Подтвердить отмену"
    return actions


@transaction.atomic
def change_status(exchange_id, actor, action):
    exchange = Exchange.objects.select_related("offered", "requested").get(
        involving(actor), pk=exchange_id,
    )
    if action not in actions_for(exchange, actor):
        raise ExchangeError("Это действие больше недоступно.")
    if action == "accept":
        accept(exchange)
    elif action == "decline":
        close(exchange, STATUS.DECLINED)
    elif action == "withdraw":
        close(exchange, STATUS.CANCELLED)
    elif action == "received":
        mark_received(exchange, actor)
    elif action == "dispute":
        exchange.status = STATUS.DISPUTED
    elif not exchange.cancel_requested_by_id:
        exchange.cancel_requested_by = actor
    else:
        close(exchange, STATUS.CANCELLED)
        book_pair(exchange).update(status=Book.Status.AVAILABLE)
    exchange.save()


@transaction.atomic
def send_message(exchange_id, actor, text):
    exchange = Exchange.objects.get(involving(actor), pk=exchange_id)
    if exchange.status not in (STATUS.PENDING, STATUS.ACCEPTED, STATUS.DISPUTED):
        raise ExchangeError("Переписка по этому обмену закрыта.")
    Message.objects.create(exchange=exchange, sender=actor, text=text)
