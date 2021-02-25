from django.contrib import admin
from world.models import Image


def make_active(modeladmin, request, queryset):
    queryset.update(active=True)


make_active.short_description = "Опубликовать выбранные объявления"


class ImageAdmin(admin.ModelAdmin):
    list_display = ['active', 'image_file', 'type', 'date', 'description', 'contacts', 'email']
    fields = ['active', 'type', 'point', 'date', 'image_url', 'image_file', 'description', 'email', 'radius', 'contacts']
    actions = [make_active]


admin.site.register(Image, ImageAdmin)
