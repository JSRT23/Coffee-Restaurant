from django.test import TestCase
from django.utils import timezone
from datetime import time, timedelta, datetime, date
from django.contrib.auth import get_user_model

from .models import Ubicacion, Mesa, EstadoReserva, Reserva
from .serializers import ReservaSerializer


class DummyRequest:
    """Minimal request-like object exposing a user attribute for serializer context."""
    def __init__(self, user):
        self.user = user


class ReservaSerializerTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='pass1234')
        self.ubicacion = Ubicacion.objects.create(nombre='Sede Centro')
        self.mesa = Mesa.objects.create(numero=1, capacidad=4, ubicacion=self.ubicacion, disponible=True, activo=True)
        self.estado = EstadoReserva.objects.create(nombre='Pendiente')
        self.fecha = timezone.localdate()

    def build_context(self, user=None):
        return {'request': DummyRequest(user or self.user)}

    def test_exceeds_capacity_is_invalid(self):
        data = {
            'mesa': self.mesa.id,
            'fecha': self.fecha.isoformat(),
            'hora_inicio': '12:00:00',
            'numero_personas': 5,  # supera capacidad=4
            'estado': self.estado.id,
        }
        serializer = ReservaSerializer(data=data, context=self.build_context())
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertTrue(any('solo admite' in str(msg) for msg in serializer.errors['non_field_errors']))

    def test_inactive_mesa_is_invalid(self):
        self.mesa.activo = False
        self.mesa.save()
        data = {
            'mesa': self.mesa.id,
            'fecha': self.fecha.isoformat(),
            'hora_inicio': '12:00:00',
            'numero_personas': 2,
            'estado': self.estado.id,
        }
        serializer = ReservaSerializer(data=data, context=self.build_context())
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertTrue(any('no está disponible' in str(msg) for msg in serializer.errors['non_field_errors']))

    def test_no_disponible_mesa_is_invalid(self):
        self.mesa.disponible = False
        self.mesa.save()
        data = {
            'mesa': self.mesa.id,
            'fecha': self.fecha.isoformat(),
            'hora_inicio': '12:00:00',
            'numero_personas': 2,
            'estado': self.estado.id,
        }
        serializer = ReservaSerializer(data=data, context=self.build_context())
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertTrue(any('no está disponible' in str(msg) for msg in serializer.errors['non_field_errors']))

    def test_overlapping_time_slot_is_invalid(self):
        # Reserva existente 12:00 - 12:15
        Reserva.objects.create(
            usuario=self.user,
            mesa=self.mesa,
            fecha=self.fecha,
            hora_inicio=time(12, 0),
            numero_personas=2,
            estado=self.estado,
        )
        # Nueva solicitud 12:10 - 12:25 (solapa)
        data = {
            'mesa': self.mesa.id,
            'fecha': self.fecha.isoformat(),
            'hora_inicio': '12:10:00',
            'numero_personas': 2,
            'estado': self.estado.id,
        }
        serializer = ReservaSerializer(data=data, context=self.build_context())
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertTrue(any('franja horaria ya está reservada' in str(msg) for msg in serializer.errors['non_field_errors']))

    def test_hora_fin_is_computed_on_create(self):
        data = {
            'mesa': self.mesa.id,
            'fecha': self.fecha.isoformat(),
            'hora_inicio': '13:30:00',
            'numero_personas': 3,
            'estado': self.estado.id,
        }
        serializer = ReservaSerializer(data=data, context=self.build_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        expected_end = (datetime.combine(date.today(), time(13, 30)) + timedelta(minutes=15)).time()
        self.assertEqual(instance.hora_fin, expected_end)
        self.assertIn('hora_fin', serializer.data)
        self.assertEqual(serializer.data['hora_fin'], expected_end.strftime('%H:%M:%S'))

    def test_usuario_is_set_from_current_user_default(self):
        data = {
            'mesa': self.mesa.id,
            'fecha': self.fecha.isoformat(),
            'hora_inicio': '14:00:00',
            'numero_personas': 2,
            'estado': self.estado.id,
        }
        serializer = ReservaSerializer(data=data, context=self.build_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        self.assertEqual(instance.usuario, self.user)

    def test_valid_reservation_is_created(self):
        data = {
            'mesa': self.mesa.id,
            'fecha': self.fecha.isoformat(),
            'hora_inicio': '15:00:00',
            'numero_personas': 4,
            'estado': self.estado.id,
            'notas': 'Ventana',
        }
        serializer = ReservaSerializer(data=data, context=self.build_context())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        self.assertIsInstance(instance, Reserva)
        self.assertEqual(instance.mesa, self.mesa)
        self.assertEqual(instance.numero_personas, 4)
        self.assertEqual(instance.estado, self.estado)
        self.assertEqual(instance.notas, 'Ventana')
