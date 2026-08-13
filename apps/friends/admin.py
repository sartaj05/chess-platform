from django.contrib import admin

from .models import Friendship, UserBlock, UserReport


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("requester", "addressee", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("requester__email", "addressee__email")


admin.site.register(UserBlock)
admin.site.register(UserReport)
