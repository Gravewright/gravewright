from django.contrib import admin

from .models import Campaign, Membership


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'system', 'created_at']
    search_fields = ['name', 'owner__email']
    inlines = [MembershipInline]
