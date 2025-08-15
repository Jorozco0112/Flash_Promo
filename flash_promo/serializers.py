from rest_framework import serializers

from django.contrib.gis.geos import Point

from .models import (
    FlashPromo,
    Reservation,
    StoreProduct,
    Store,
    Product,
)
from .constants import FlashPromoStatus



class PromoListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="store_product.product.name")
    store_name = serializers.CharField(source="store_product.store.name")
    distance_m = serializers.FloatField(read_only=True)

    class Meta:
        model = FlashPromo
        fields = (
            "id",
            "product_name",
            "store_name",
            "promo_price",
            "starts_at",
            "ends_at",
            "distance_m"
        )


class ReservationCreateSerializer(serializers.Serializer):
    promo_id = serializers.IntegerField(required=True)


class ReservationResponseSerializer(serializers.Serializer):
    reservation_token = serializers.CharField()
    expires_at = serializers.DateTimeField()


class ReservationTokenSerializer(serializers.Serializer):
    reservation_token = serializers.CharField(required=True)


class ReservationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = (
            "token",
            "status",
            "expires_at"
        )


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name", "sku", "brand", "category")
        extra_kwargs = {"sku": {"required": True}}

# ---------- Store ----------
class StoreSerializer(serializers.ModelSerializer):

    lat = serializers.FloatField(write_only=True, required=True)
    lon = serializers.FloatField(write_only=True, required=True)

    class Meta:
        model = Store
        fields = ("id", "name", "lat", "lon")

    def create(self, validated_data):
        lat = validated_data.pop("lat")
        lon = validated_data.pop("lon")
        return Store.objects.create(geom=Point(lon, lat), **validated_data)

    def update(self, instance, validated_data):
        lat = validated_data.pop("lat", None)
        lon = validated_data.pop("lon", None)

        if lat is not None and lon is not None:
            instance.geom = Point(lon, lat)

        instance.name = validated_data.get("name", instance.name)
        instance.save()
        return instance

# ---------- StoreProduct ----------
class StoreProductSerializer(serializers.ModelSerializer):
    store_id = serializers.IntegerField(write_only=True)
    product_id = serializers.IntegerField(write_only=True)
    store = serializers.CharField(source="store.name", read_only=True)
    product = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = StoreProduct
        fields = ("id", "store_id", "product_id", "store", "product", "stock", "base_price")

    def validate(self, attrs):
        from .models import Store, Product, StoreProduct
        store_id = attrs.get("store_id")
        product_id = attrs.get("product_id")

        try:
            store = Store.objects.get(pk=store_id)
        except Store.DoesNotExist:
            raise serializers.ValidationError({"store_id": "Store no existe."})
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product_id": "Product no existe."})

        # Unique Together(store, product)
        exists = StoreProduct.objects.filter(store_id=store_id, product_id=product_id).exists()
        if exists and not self.instance:
            raise serializers.ValidationError("Ya existe un StoreProduct para ese store/product.")

        attrs["_store"] = store
        attrs["_product"] = product
        return attrs

    def create(self, validated_data):
        store = validated_data.pop("_store")
        product = validated_data.pop("_product")
        return StoreProduct.objects.create(store=store, product=product, **validated_data)

    def update(self, instance, validated_data):

        validated_data.pop("_store", None)
        validated_data.pop("_product", None)
        validated_data.pop("store_id", None)
        validated_data.pop("product_id", None)
        return super().update(instance, validated_data)



class FlashPromoCreateSerializer(serializers.ModelSerializer):
    store_product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = FlashPromo
        fields = ("store_product_id", "promo_price", "starts_at", "ends_at")
        extra_kwargs = {
            "promo_price": {"min_value": 0},
        }

    def validate(self, attrs):
        sp_id = attrs.get("store_product_id")
        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")

        # Validates store product exists
        try:
            sp = StoreProduct.objects.select_related("product").get(pk=sp_id)
        except StoreProduct.DoesNotExist:
            raise serializers.ValidationError({"store_product_id": "StoreProduct does not exist."})

        # Validates scheduled time
        if not starts_at or not ends_at or starts_at >= ends_at:
            raise serializers.ValidationError({"starts_at": "starts_at must be < ends_at."})


        if (ends_at - starts_at).total_seconds() < 60:
            raise serializers.ValidationError("scheduled time have to be at least 1 min.")

        # Validate promo price have to be less than base price
        promo_price = attrs.get("promo_price")
        if promo_price is None or promo_price >= sp.base_price:
            raise serializers.ValidationError(
                {"promo_price": "Promo price have to be less than base price."}
            )

        # Save the objet to use in create method
        attrs["_store_product_obj"] = sp
        return attrs

    def create(self, validated_data):
        sp = validated_data.pop("_store_product_obj")
        # Create the promo with scheduled status, then celery task update to active
        promo = FlashPromo.objects.create(
            store_product=sp,
            status=FlashPromoStatus.SCHEDULED,
            **validated_data
        )
        return promo
