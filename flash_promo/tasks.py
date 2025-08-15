from celery import shared_task, group
from django.utils import timezone

from flash_promo.constants import FlashPromoStatus
from flash_promo.models import FlashPromo, NotificationLog
from flash_promo.services import profiles_to_notify_for_promo

BATCH_SIZE = 1000

@shared_task
def activate_and_notify_promos():
    now = timezone.now()
    # Here activate the flash promo for certain products
    to_activate = FlashPromo.objects.filter(
        status=FlashPromoStatus.SCHEDULED,
        starts_at__lte=now,
        ends_at__gt=now
    )
    for promo in to_activate:
        promo.status = FlashPromoStatus.ACTIVE
        promo.save(update_fields=["status"])
        notify_promo.delay(promo.id)

    # Here we FINISHED the promo that end_at is equal to now (Basically, expired)
    FlashPromo.objects.filter(
        status=FlashPromoStatus.ACTIVE,
        ends_at__lt=now
    ).update(status=FlashPromoStatus.FINISHED)


@shared_task
def notify_promo(promo_id: int):
    promo = FlashPromo.objects.get(pk=promo_id)
    user_ids = list(profiles_to_notify_for_promo(promo).values_list("user_id", flat=True))
    jobs = []
    for i in range(0, len(user_ids), BATCH_SIZE):
        jobs.append(send_push_batch.s(promo_id, user_ids[i:i+BATCH_SIZE]))

    if jobs:
        group(jobs).apply_async()

@shared_task
def send_push_batch(promo_id: int, user_ids: list[int]):
    # Register those notification that already and avoid spam(anti spam strategy)

    objs = [NotificationLog(user_id=uid, promo_id=promo_id) for uid in user_ids]
    NotificationLog.objects.bulk_create(objs, ignore_conflicts=True)


@shared_task
def notify_active_promos():
    now = timezone.now()
    actives = FlashPromo.objects.filter(
        status=FlashPromoStatus.ACTIVE,
        starts_at__lte=now,
        ends_at__gte=now
    )
    for promo in actives:
        notify_promo.delay(promo.id)
