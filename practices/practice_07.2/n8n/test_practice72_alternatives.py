from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from books.models import Book


class EquivalentEditionTest(TestCase):
    def test_same_title_precedes_same_author(self):
        owner = get_user_model().objects.create_user(username="reader")

        def book(title, author):
            return Book.objects.create(owner=owner, title=title, author=author,
                                       description="Хорошее состояние", wanted="Любая книга",
                                       photo="covers/test.jpg")

        current = book("Дюна", "Фрэнк Герберт")
        edition = book("ДЮНА", "Другой автор")
        book("Мессия Дюны", "Фрэнк Герберт")
        book("Дюна 2", "Другой автор")
        response = self.client.get(reverse("book", args=[current.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["related"][0].pk, edition.pk,
            "same-title edition should appear before another book by the same author",
        )
