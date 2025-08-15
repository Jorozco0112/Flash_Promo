import uuid
from datetime import timedelta
from django.db import transaction, models
from django.utils import timezone
from django.contrib.gis.measure import D
from flash_promo.models import (
    Profile,
    FlashPromo,
    NotificationLog,
    Reservation,
    StoreProduct
)
from flash_promo.constants import MINIMUM_DISTANCE, ReservationStatus

def eligible_profiles_for_promo(promo: FlashPromo) -> models.QuerySet[Profile]:
    """This function have the purpose
    to return those profile that meet
    the filters"""

    store_product = promo.store_product
    store = store_product.store
    profile_behavior_filter = models.Q(is_new_user=True) | models.Q(is_frequent=True)

    return (
        Profile.objects
        .filter(profile_behavior_filter)
        .filter(geom__distance_lte=(store.geom, D(m=MINIMUM_DISTANCE)))
    )


def profiles_to_notify_for_promo(promo: FlashPromo):
    """This function only return the profiles
    that can be notify by the promo"""

    today = timezone.localdate()
    profiles = eligible_profiles_for_promo(promo)
    already_notified_ids = (
        NotificationLog.objects
        .filter(promo=promo, sent_date=today)
        .values_list("user_id", flat=True)
    )

    return profiles.exclude(user_id__in=already_notified_ids)


@transaction.atomic
def hold_store_product_db(user, promo: FlashPromo) -> Reservation:
    """This function initiates the process of
    reservation for a given store product promo"""
    store_product = StoreProduct.objects.select_for_update().get(pk=promo.store_product_id)

    if store_product.stock <= 0:
        raise ValueError("No stock for ")

    store_product.stock -= 1
    store_product.save(update_fields=["stock"])

    reservation = Reservation.objects.create(
        promo=promo,
        store_product=store_product,
        user=user,
        status=ReservationStatus.HOLD,
        token=uuid.uuid4().hex,
        expires_at=timezone.now() + timedelta(minutes=1),
    )
    return reservation



def confirm_reservation(token: str, user):
    """This function confirme the reservation
    reservation of store product promo"""

    expired = False
    not_hold = False
    reservation_promo = None

    with transaction.atomic():
        # Lock de la reserva para evitar carreras
        reservation_promo = (
            Reservation.objects
            .select_for_update()
            .select_related("store_product")
            .get(token=token, user=user)
        )

        # 1) Estado inválido (no confirmamos ni tocamos stock)
        if reservation_promo.status != ReservationStatus.HOLD:
            not_hold = True
        else:
            if reservation_promo.expires_at <= timezone.now():
                StoreProduct.objects.filter(
                    pk=reservation_promo.store_product_id
                ).update(stock=models.F("stock") + 1)
                reservation_promo.status = ReservationStatus.EXPIRED
                reservation_promo.save(update_fields=["status"])
                expired = True
            else:
                reservation_promo.status = ReservationStatus.CONFIRMED
                reservation_promo.save(update_fields=["status"])


    if not_hold:
        raise ValueError("Reservation not in HOLD state")

    if expired:
        raise ValueError("Reservation expired")

    return reservation_promo


@transaction.atomic
def cancel_or_expire_reservation(reservation: Reservation):
    """This function cancel or expired
    the given reservation promo"""

    if reservation.status != ReservationStatus.HOLD:
        return reservation

    store_product = StoreProduct.objects.select_for_update().get(pk=reservation.store_product_id)
    store_product.stock += 1
    store_product.save(update_fields=["stock"])

    reservation.status = ReservationStatus.EXPIRED
    reservation.save(update_fields=["status"])

    return reservation
