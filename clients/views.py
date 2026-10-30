import json
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .forms import ClientForm
from .models import Client


def api_login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'message': 'Tu sesión terminó. Vuelve a iniciar sesión.'}, status=401)
        return view(request, *args, **kwargs)
    return wrapped


def serialize(client):
    return {field: getattr(client, field) for field in ['id', 'name', 'company', 'email', 'phone', 'status']} | {
        'created_at': client.created_at.isoformat(), 'updated_at': client.updated_at.isoformat()}


def save_client(request, instance=None):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'message': 'No se pudo leer la información enviada.'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'message': 'El formulario debe contener un objeto.'}, status=400)
    form = ClientForm(data, instance=instance)
    if not form.is_valid():
        return JsonResponse({'message': 'Revisa los campos indicados.', 'errors': form.errors}, status=400)
    try:
        client = form.save()
    except IntegrityError:
        return JsonResponse({'message': 'Ya existe un cliente con este correo.',
                             'errors': {'email': ['Este correo ya está registrado.']}}, status=400)
    return JsonResponse({'client': serialize(client)}, status=200 if instance else 201)


@login_required
@ensure_csrf_cookie
def dashboard(request):
    return render(request, 'clients/dashboard.html')


@api_login_required
@require_http_methods(['GET', 'POST'])
def client_collection(request):
    if request.method == 'POST':
        return save_client(request)
    clients = Client.objects.all()
    totals = clients.aggregate(total=Count('id'), prospect=Count('id', filter=Q(status='prospect')),
        customer=Count('id', filter=Q(status='customer')), inactive=Count('id', filter=Q(status='inactive')))
    query = request.GET.get('q', '').strip()
    if query:
        clients = clients.filter(Q(name__icontains=query) | Q(company__icontains=query))
    status = request.GET.get('status', '')
    if status:
        if status not in Client.Status.values:
            return JsonResponse({'message': 'Selecciona un estado válido.'}, status=400)
        clients = clients.filter(status=status)
    page = Paginator(clients, 8).get_page(request.GET.get('page', 1))
    return JsonResponse({'clients': [serialize(c) for c in page], 'metrics': totals,
        'pagination': {'page': page.number, 'pages': page.paginator.num_pages, 'total': page.paginator.count}})


@api_login_required
@require_http_methods(['GET', 'PUT', 'DELETE'])
def client_detail(request, pk):
    try:
        client = Client.objects.get(pk=pk)
    except Client.DoesNotExist:
        return JsonResponse({'message': 'Este cliente ya no existe.'}, status=404)
    if request.method == 'GET':
        return JsonResponse({'client': serialize(client)})
    if request.method == 'DELETE':
        client.delete()
        return JsonResponse({'message': 'Cliente eliminado.'})
    return save_client(request, instance=client)


@require_http_methods(['GET'])
def health(request):
    return JsonResponse({'status': 'ok'})
