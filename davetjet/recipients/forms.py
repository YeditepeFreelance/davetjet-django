import re
from django import forms
from .models import Recipient

class RecipientForm(forms.ModelForm):
    phone_number = forms.CharField(
        label="Telefon",
        max_length=20,
        required=True,
        help_text="5XXXXXXXXX formatında girin",
        widget=forms.TextInput(attrs={"placeholder": "5XXXXXXXXX"})
    )

    class Meta:
        model = Recipient
        fields = ["name", "email", "phone_number"]
        labels = {
            "name": "Ad",
            "email": "E-posta",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ad Soyad"}),
            "email": forms.EmailInput(attrs={"placeholder": "ornek@eposta.com"}),
        }

    def clean_phone_number(self):
        raw = (self.cleaned_data.get("phone_number") or "").strip()
        digits = re.sub(r"\D+", "", raw)

        # 90/0 öneklerini kırp → 5XXXXXXXXX formatına normalize et
        if digits.startswith("90") and len(digits) >= 12:
            digits = digits[2:]
        if digits.startswith("0") and len(digits) >= 11:
            digits = digits[1:]

        if len(digits) != 10 or not digits.startswith("5"):
            raise forms.ValidationError("Telefonu 5XXXXXXXXX şeklinde girin.")
        return digits

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()
