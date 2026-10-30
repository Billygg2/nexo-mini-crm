from django.db import models
from django.db.models.functions import Lower
from django.core.validators import RegexValidator


class Client(models.Model):
    class Status(models.TextChoices):
        PROSPECT = 'prospect', 'Prospecto'
        CUSTOMER = 'customer', 'Cliente'
        INACTIVE = 'inactive', 'Inactivo'

    name = models.CharField('nombre', max_length=120)
    company = models.CharField('empresa', max_length=160, blank=True)
    email = models.EmailField('correo', unique=True)
    phone = models.CharField('teléfono', max_length=30, blank=True, validators=[
        RegexValidator(r'^\+?[0-9\s().-]{6,30}$', 'Introduce un teléfono válido (6 a 30 caracteres).')])
    status = models.CharField('estado', max_length=12, choices=Status.choices, default=Status.PROSPECT)
    created_at = models.DateTimeField('fecha de registro', auto_now_add=True)
    updated_at = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        verbose_name = 'cliente'
        constraints = [models.UniqueConstraint(Lower('email'), name='client_email_case_insensitive')]

    def __str__(self):
        return self.name
