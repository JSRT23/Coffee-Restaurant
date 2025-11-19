from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'rol', 'is_staff', 'date_joined')
    list_filter = ('rol', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')

    fieldsets = UserAdmin.fieldsets + (
        ('Rol', {'fields': ('rol',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Rol', {'fields': ('rol',)}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Solo admin puede asignar MESERO o ADMIN
        if not request.user.is_superuser:
            form.base_fields['rol'].choices = [('CLIENTE', 'Cliente')]
        return form