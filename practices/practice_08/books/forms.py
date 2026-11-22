from io import BytesIO

from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Book, Message, ReadBook


class EmailForm(forms.Form):
    email = forms.EmailField(label="Электронная почта", max_length=150)

    def clean_email(self):
        return self.cleaned_data["email"].lower()


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Электронная почта", max_length=150)

    def clean_username(self):
        return self.cleaned_data["username"].lower()


class ActivateForm(SetPasswordForm):
    name = forms.CharField(label="Имя в профиле", max_length=100)
    field_order = ["name", "new_password1", "new_password2"]


class BookForm(forms.ModelForm):
    photo = forms.FileField(label="Фото состояния", widget=forms.ClearableFileInput(
        attrs={"accept": "image/jpeg,image/png,image/webp"},
    ))

    class Meta:
        model = Book
        fields = ["title", "author", "photo", "description", "wanted"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4}),
                   "wanted": forms.Textarea(attrs={"rows": 3})}

    def clean_photo(self):
        photo = self.cleaned_data["photo"]
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Размер фото должен быть не больше 5 МБ.")
        try:
            with Image.open(photo, formats=["JPEG", "PNG", "WEBP"]) as source:
                if source.width * source.height > 20_000_000:
                    raise forms.ValidationError("Слишком большое разрешение фото.")
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((1400, 1400))
                output = BytesIO()
                image.save(output, format="JPEG", quality=85)
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise forms.ValidationError("Загрузите корректное фото в JPEG, PNG или WebP.") from None
        return ContentFile(output.getvalue(), name="cover.jpg")


class ReadBookForm(forms.ModelForm):
    class Meta:
        model = ReadBook
        fields = ["title", "author"]


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3})}


class OfferForm(forms.Form):
    offered = forms.ModelChoiceField(
        label="Какую книгу предлагаете", queryset=Book.objects.none(), empty_label="Выберите книгу",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    text = forms.CharField(
        label="Сообщение владельцу", max_length=2000,
        widget=forms.Textarea(attrs={
            "class": "form-control", "rows": 4, "placeholder": "Напишите, в каком состоянии ваша книга",
        }),
    )

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["offered"].queryset = Book.objects.filter(
            owner=owner, status=Book.Status.AVAILABLE,
        )
