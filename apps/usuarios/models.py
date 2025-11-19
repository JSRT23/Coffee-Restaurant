from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UsuarioManager(BaseUserManager):
    def create_user(self, username, email, password=None, rol='CLIENTE'):
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            rol=rol
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None):
        user = self.create_user(
            username, email, password=password, rol='ADMIN')
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class Usuario(AbstractUser):
    ROLES = (
        ('ADMIN', 'Administrador'),
        ('CLIENTE', 'Cliente'),
        ('MESERO', 'Mesero'),
        ('COCINERO', 'Cocinero'),
    )
    rol = models.CharField(max_length=20, choices=ROLES, default='CLIENTE')

    objects = UsuarioManager()

    def __str__(self):
        return f"{self.username} - {self.rol}"
