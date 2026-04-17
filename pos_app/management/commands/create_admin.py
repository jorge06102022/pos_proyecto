from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="wiliam",
                password="12345678",
                email="admin@gmail.com"
            )
            self.stdout.write(self.style.SUCCESS("Admin creado"))