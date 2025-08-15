from django.contrib.gis.db import models as gmodels
from django.contrib.postgres.indexes import GistIndex
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from flash_promo.constants import FlashPromoStatus, ReservationStatus



class Profile(gmodels.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="user_profile"
    )

    # WGS84 lat/lon - ubicacion del cliente
    geom = gmodels.PointField(geography=True, null=True, blank=True)

    # Comportamiento Del cliente
    is_new_user = models.BooleanField(default=False)
    is_frequent = models.BooleanField(default=False)

    class Meta:
        indexes = [GistIndex(fields=["geom"])]

    def __str__(self):
        return f"Profile({self.pk})"


class Store(gmodels.Model):
    name = models.CharField(max_length=120)
    geom = gmodels.PointField(geography=True)

    class Meta:
        indexes = [GistIndex(fields=["geom"])]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=64, unique=True)
    brand = models.CharField(max_length=64, blank=True)
    category = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"


class StoreProduct(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    stock = models.PositiveIntegerField(default=0)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = [("store", "product")]

    def __str__(self):
        return f"{self.store} - {self.product}"


class FlashPromo(models.Model):
    store_product = models.ForeignKey(StoreProduct, on_delete=gmodels.CASCADE)
    promo_price = models.DecimalField(max_digits=12, decimal_places=2)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(
        max_length=12,
        choices=FlashPromoStatus.choices,
        default=FlashPromoStatus.SCHEDULED,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(starts_at__lt=models.F("ends_at")),
                name="promo_valid_window",
            )
        ]
        indexes = [
            models.Index(fields=["status", "starts_at", "ends_at"]),
            models.Index(fields=["store_product", "starts_at"]),
        ]

    def __str__(self):
        return f"Promo({self.pk}) {self.store_product} - {self.promo_price}"


class NotificationLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    promo = models.ForeignKey(FlashPromo, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_date = models.DateField(default=timezone.localdate)

    class Meta:
        unique_together = [("user", "promo", "sent_date")]
        indexes = [models.Index(fields=["promo", "sent_at"])]

    def __str__(self):
        return f"Notif({self.user_id}, {self.promo_id}, {self.sent_date})"


class Reservation(models.Model):
    promo = models.ForeignKey(FlashPromo, on_delete=models.PROTECT)
    store_product = models.ForeignKey(StoreProduct, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=12,
        choices=ReservationStatus.choices,
        default=ReservationStatus.HOLD,
    )
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["store_product", "status"])]

    def __str__(self):
        return f"Res({self.token}) {self.status}"
