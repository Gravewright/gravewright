from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import AdminUserChangeForm, AdminUserCreationForm
from .models import User


@admin.register(User)
class AccountAdmin(UserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    list_display = ("email", "name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    ordering = ("email",)
    search_fields = ("email", "name")
    readonly_fields = ("date_joined", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser",
                                    "groups", "user_permissions")}),
        ("Dates", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = ((None, {"fields": ("email", "name", "role", "password1", "password2")}),)
