from django.contrib.auth.models import User

def create_admin():
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(
            username="wiliam",
            email="jordav8a@gmail.com",
            password="12345678"
        )