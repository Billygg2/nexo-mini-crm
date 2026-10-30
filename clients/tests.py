import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client as HttpClient, TestCase
from django.urls import reverse

from .models import Client


class ClientTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('reviewer', password='test-only-password')

    def setUp(self):
        self.client.force_login(self.user)
        self.data = {'name': 'Ana Pérez', 'company': 'Estudio Norte', 'email': 'ana@example.com',
                     'phone': '+593 99 123 4567', 'status': 'prospect'}

    def post(self, data):
        return self.client.post(reverse('client-list'), data=json.dumps(data), content_type='application/json')

    def test_dashboard_and_login(self):
        self.assertContains(self.client.get('/'), 'Tu directorio')
        self.client.logout()
        self.assertRedirects(self.client.get('/'), '/login/?next=/')
        self.assertEqual(self.client.get(reverse('client-list')).status_code, 401)

    def test_create_and_persist(self):
        response = self.post(self.data)
        self.assertEqual(response.status_code, 201)
        client = Client.objects.get()
        self.assertEqual(client.name, self.data['name'])
        self.assertIsNotNone(client.created_at)
        self.assertIsNotNone(client.updated_at)

    def test_update_and_detail(self):
        pk = self.post(self.data).json()['client']['id']
        self.data.update(status='customer', company='Nueva empresa')
        url = reverse('client-detail', args=[pk])
        self.assertEqual(self.client.put(url, json.dumps(self.data), content_type='application/json').status_code, 200)
        self.assertEqual(self.client.get(url).json()['client']['company'], 'Nueva empresa')
        self.assertEqual(Client.objects.get().status, 'customer')

    def test_delete_and_missing_client(self):
        pk = self.post(self.data).json()['client']['id']
        url = reverse('client-detail', args=[pk])
        self.assertEqual(self.client.delete(url).status_code, 200)
        self.assertFalse(Client.objects.exists())
        for method in ['get', 'put', 'delete']:
            self.assertEqual(getattr(self.client, method)(url).status_code, 404)

    def test_required_fields_and_bad_values(self):
        for field, value in [('name', '  '), ('email', 'invalid'), ('status', 'other'), ('phone', 'letters')]:
            with self.subTest(field=field):
                response = self.post(self.data | {field: value})
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()['errors'])
        self.assertEqual(self.post({}).status_code, 400)
        self.assertEqual(Client.objects.count(), 0)

    def test_optional_fields(self):
        self.data.update(company='', phone='')
        self.assertEqual(self.post(self.data).status_code, 201)

    def test_email_is_unique_and_normalized(self):
        self.assertEqual(self.post(self.data | {'email': 'ANA@EXAMPLE.COM'}).status_code, 201)
        self.assertEqual(Client.objects.get().email, 'ana@example.com')
        self.assertEqual(self.post(self.data).status_code, 400)
        self.assertEqual(Client.objects.count(), 1)

    def test_search_and_status_filter(self):
        self.post(self.data)
        self.post(self.data | {'name': 'Pedro', 'company': 'Otro estudio', 'email': 'pedro@example.com', 'status': 'customer'})
        for query in ['ana', 'NORTE']:
            result = self.client.get(reverse('client-list'), {'q': query}).json()
            self.assertEqual(result['pagination']['total'], 1)
        result = self.client.get(reverse('client-list'), {'status': 'customer'}).json()
        self.assertEqual(result['clients'][0]['name'], 'Pedro')
        self.assertEqual(result['metrics']['total'], 2)
        self.assertEqual(result['metrics']['prospect'], 1)
        self.assertEqual(result['metrics']['customer'], 1)
        self.assertEqual(self.client.get(reverse('client-list'), {'q': 'ana', 'status': 'inactive'}).json()['clients'], [])
        self.assertEqual(self.client.get(reverse('client-list'), {'status': 'invalid'}).status_code, 400)

    def test_pagination(self):
        for index in range(10):
            self.post(self.data | {'email': f'person{index}@example.com'})
        result = self.client.get(reverse('client-list')).json()
        self.assertEqual(len(result['clients']), 8)
        second = self.client.get(reverse('client-list'), {'page': 2}).json()
        self.assertEqual(len(second['clients']), 2)
        self.assertEqual(second['pagination']['pages'], 2)

    def test_malformed_json(self):
        for payload in ['{broken', '[]', 'null']:
            response = self.client.post(reverse('client-list'), payload, content_type='application/json')
            self.assertEqual(response.status_code, 400)

    def test_csrf_is_enforced(self):
        browser = HttpClient(enforce_csrf_checks=True)
        browser.force_login(self.user)
        url = reverse('client-list')
        self.assertEqual(browser.post(url, self.data).status_code, 403)
        browser.get('/')
        response = browser.post(url, json.dumps(self.data), content_type='application/json',
                                HTTP_X_CSRFTOKEN=browser.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 201)

    def test_seed_is_idempotent(self):
        call_command('seed_demo', stdout=StringIO())
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Client.objects.count(), 12)

    def test_api_requires_login_for_writes(self):
        self.client.logout()
        self.assertEqual(self.post(self.data).status_code, 401)
        self.assertEqual(self.client.delete('/api/clients/1/').status_code, 401)

    def test_admin_requires_staff(self):
        self.assertEqual(self.client.get('/admin/clients/client/').status_code, 302)
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.assertEqual(self.client.get('/admin/clients/client/').status_code, 200)

    def test_health_endpoint(self):
        self.client.logout()
        self.assertEqual(self.client.get('/health/').json(), {'status': 'ok'})
