from django.core.management.base import BaseCommand
from clients.models import Client


class Command(BaseCommand):
    help = 'Carga clientes ficticios de ejemplo sin duplicar registros ni crear usuarios.'

    def handle(self, *args, **options):
        rows = [
            ('Sofía Andrade', 'Estudio Oliva', 'sofia', 'customer'),
            ('Mateo Rivas', 'Norte Arquitectura', 'mateo', 'prospect'),
            ('Valentina Torres', 'Casa Botánica', 'valentina', 'customer'),
            ('Andrés Molina', 'Molina & Asociados', 'andres', 'prospect'),
            ('Camila Vega', 'Café Bruma', 'camila', 'customer'),
            ('Diego Salazar', 'Órbita Digital', 'diego', 'inactive'),
            ('Isabella Luna', 'Luna Concept', 'isabella', 'prospect'),
            ('Nicolás Paredes', 'Taller Sur', 'nicolas', 'customer'),
            ('Lucía Cevallos', 'Marea Studio', 'lucia', 'customer'),
            ('Daniel Costa', 'Costa Editorial', 'daniel', 'inactive'),
            ('Emilia Ruiz', 'Punto Verde', 'emilia', 'prospect'),
            ('Sebastián León', 'Forma Interior', 'sebastian', 'customer'),
        ]
        created = 0
        for index, (name, company, alias, status) in enumerate(rows):
            _, new = Client.objects.get_or_create(email=f'{alias}@example.com', defaults={
                'name': name, 'company': company, 'phone': f'09900000{index:02}', 'status': status})
            created += new
        self.stdout.write(self.style.SUCCESS(f'{created} clientes ficticios creados.'))
