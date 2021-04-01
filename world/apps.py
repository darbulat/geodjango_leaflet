from django.apps import AppConfig


class WorldConfig(AppConfig):
    name = 'world'

    def ready(self):
        import world.signals
