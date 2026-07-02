from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import EmailOTP, User
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",); list_display = ("email", "display_name", "is_email_verified", "two_factor_enabled", "is_active", "is_staff", "last_seen_at")
    list_filter = ("is_active", "is_staff", "is_superuser", "is_email_verified", "two_factor_enabled"); search_fields = ("email", "display_name", "first_name", "last_name")
    readonly_fields = ("date_joined", "last_login", "last_seen_at")
    fieldsets = ((None, {"fields": ("email", "password")}), ("Personal info", {"fields": ("first_name", "last_name", "display_name", "bio", "avatar", "country", "time_zone")}), ("Security", {"fields": ("is_email_verified", "two_factor_enabled", "totp_secret")}), ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}), ("Important dates", {"fields": ("last_login", "date_joined", "last_seen_at")}))
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2", "is_email_verified", "is_staff", "is_active")}),)
@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "expires_at", "used_at", "attempts", "created_at"); list_filter = ("purpose", "used_at", "created_at"); search_fields = ("user__email",); readonly_fields = ("code_hash", "created_at", "updated_at")
