from django import forms
from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'company', 'email', 'phone', 'status']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        duplicates = Client.objects.filter(email__iexact=email)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('Ya existe un cliente con este correo.')
        return email
