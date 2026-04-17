from django.apps import AppConfig

class PosAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pos_app'

    def ready(self):
        from .admin_init import create_admin
        create_admin()