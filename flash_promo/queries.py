from django.utils.timezone import now
from django.contrib.gis.measure import D

from flash_promo.models import FlashPromo, Store, Profile, User
from flash_promo.constants import MINIMUM_DISTANCE, FlashPromoStatus


class ProfileDoesNotExist(Exception):
    pass



def _behavior_ok(profile) -> bool:
    # ✅ usa los booleanos de tu modelo
    return bool(profile.is_new_user or profile.is_frequent)


def active_promos_for_profile(profile: Profile, radius_m: int = MINIMUM_DISTANCE):
    """
    Active flash promos filter by minimum distance and ordered by distance
    Query de promos activas para un profile, filtradas por radio y ordenadas por distancia.
    """

    if not _behavior_ok(profile):
        return FlashPromo.objects.none()

    active_promos = (
        FlashPromo.objects
        .filter(status=FlashPromoStatus.ACTIVE, starts_at__lte=now(), ends_at__gte=now())
        .filter(store_product__store__geom__distance_lte=(profile.geom, D(m=radius_m)))
        .select_related("store_product", "store_product__store", "store_product__product")
        .distinct()
    )

    return active_promos


def user_is_eligible_for_promo(
    profile,
    promo: FlashPromo,
    radius_m: int = MINIMUM_DISTANCE
) -> bool:
    """
    Validates if the user meet both conditions:
    Behavior and distance
    """
    if not _behavior_ok(profile):
        return False

    store = promo.store_product.store

    return Store.objects.filter(
        pk=store.pk, geom__distance_lte=(profile.geom, D(m=radius_m))
    ).exists()


def get_profile_by_user(user: User):
    """This function consult DB and
    return the profile asociated with the user"""
    try:
        profile = Profile.objects.get(user=user)
        return profile
    except Profile.DoesNotExist:
        raise ProfileDoesNotExist(
            f"The user: {user.username} does not have a profile related"
        )
