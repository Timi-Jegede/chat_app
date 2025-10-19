from django.contrib import admin
from .models import Message, SharedFile, Profile, BackgroundOption

# Register your models here.
admin.site.register(Message)
admin.site.register(SharedFile)
admin.site.register(Profile)
admin.site.register(BackgroundOption)
admin.site.site_header = 'Admin Panel'
