import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

app = Celery("app")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descubre tasks.py en todas las apps instaladas
app.autodiscover_tasks()

# 🔒 Importa explícitamente tus tasks para registrar el nombre exacto
app.conf.imports = app.conf.imports or []
if "flash_promo.tasks" not in app.conf.imports:
    app.conf.imports.append("flash_promo.tasks")

# Beat schedule
app.conf.beat_schedule = {
    "activate-and-notify-promos": {
        "task": "flash_promo.tasks.activate_and_notify_promos",
        "schedule": 30.0,
    },
    "notify-active-promos": {
        "task": "flash_promo.tasks.notify_active_promos",
        "schedule": 30.0,
    },
}
