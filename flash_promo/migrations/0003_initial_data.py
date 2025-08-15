from django.db import migrations
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.contrib.auth.hashers import make_password

from flash_promo.constants import FlashPromoStatus

def seed_forward(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("flash_promo", "Profile")
    Store = apps.get_model("flash_promo", "Store")
    Product = apps.get_model("flash_promo", "Product")
    StoreProduct = apps.get_model("flash_promo", "StoreProduct")
    FlashPromo = apps.get_model("flash_promo", "FlashPromo")


    username = "tester"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"is_active": True, "password": make_password("test12345")},
    )
    if not created:
        # si ya existía, asegúrate de que tenga password
        if not user.password:
            user.password = make_password("test12345")
            user.save(update_fields=["password"])

    user_point = Point(-74.8069, 10.9685)  # (lon, lat)
    Profile.objects.update_or_create(
        user_id=user.id,
        defaults={
            "geom": user_point,
            "is_new_user": True,
            "is_frequent": True
        },
    )

    # 3) Tienda, producto y stock
    store, _ = Store.objects.get_or_create(
        name="Tienda Centro",
        defaults={"geom": Point(-74.81, 10.97)},
    )
    product, _ = Product.objects.get_or_create(
        sku="SKU-SEED-001",
        defaults={"name": "Agua 600ml", "brand": "AquaBrand", "category": "Bebidas"},
    )
    sp, _ = StoreProduct.objects.get_or_create(
        store=store, product=product,
        defaults={"stock": 20, "base_price": "3.50"},
    )

    # 4) Promo ACTIVA (sin lookups en update_or_create)
    now = timezone.now()
    promo, created = FlashPromo.objects.get_or_create(
        store_product=sp,
        defaults={
            "promo_price": "2.50",
            "starts_at": now - timezone.timedelta(minutes=5),
            "ends_at": now + timezone.timedelta(hours=2),
            "status": FlashPromoStatus.ACTIVE,
        },
    )
    if not created:
        # si ya existía, la dejamos activa y ajustamos ventana
        promo.promo_price = "2.50"
        promo.starts_at = now - timezone.timedelta(minutes=5)
        promo.ends_at = now + timezone.timedelta(hours=2)
        promo.status = FlashPromoStatus.ACTIVE
        promo.save()

def seed_reverse(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("flash_promo", "Profile")
    Store = apps.get_model("flash_promo", "Store")
    Product = apps.get_model("flash_promo", "Product")
    StoreProduct = apps.get_model("flash_promo", "StoreProduct")
    FlashPromo = apps.get_model("flash_promo", "FlashPromo")

    try:
        user = User.objects.get(username="tester")
        Profile.objects.filter(user_id=user.id).delete()
        user.delete()
    except User.DoesNotExist:
        pass

    try:
        product = Product.objects.get(sku="SKU-SEED-001")
    except Product.DoesNotExist:
        product = None

    if product:
        FlashPromo.objects.filter(store_product__product=product).delete()
        StoreProduct.objects.filter(product=product).delete()
        product.delete()

    Store.objects.filter(name="Tienda Centro").delete()


class Migration(migrations.Migration):

    dependencies = [
        ('flash_promo', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(seed_forward, reverse_code=seed_reverse),
    ]
