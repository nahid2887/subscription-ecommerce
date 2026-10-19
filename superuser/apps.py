from django.apps import AppConfig


class SuperuserConfig(AppConfig):
    name = 'superuser'

    def ready(self):
        import superuser.models  # noqa
