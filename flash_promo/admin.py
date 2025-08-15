from django.contrib import admin
from django.contrib.gis import admin as geoadmin
from django.utils import timezone

from .models import (
    Profile, Store, Product, StoreProduct,
    FlashPromo, NotificationLog, Reservation
)
from .constants import FlashPromoStatus, ReservationStatus


# ---------- Inlines ----------
class StoreProductInline(admin.TabularInline):
    model = StoreProduct
    extra = 0
    autocomplete_fields = ("product",)
    fields = ("product", "stock", "base_price")
    show_change_link = True


# ---------- Geo admins ----------
@admin.register(Profile)
class ProfileAdmin(geoadmin.GISModelAdmin):
    list_display = ("id", "user", "is_new_user", "is_frequent")
    list_filter = ("is_new_user", "is_frequent")
    search_fields = ("user__username", "user__email")
    autocomplete_fields = ("user",)
    default_zoom = 12
    default_lat = 10.9685
    default_lon = -74.8069
    # Mejora de rendimiento cuando listes muchos perfiles
    list_select_related = ("user",)


@admin.register(Store)
class StoreAdmin(geoadmin.GISModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    inlines = [StoreProductInline]
    default_zoom = 12
    default_lat = 10.9685
    default_lon = -74.8069


# ---------- Catálogo ----------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sku", "brand", "category")
    search_fields = ("name", "sku", "brand", "category")
    list_filter = ("brand", "category")


@admin.register(StoreProduct)
class StoreProductAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "product", "stock", "base_price")
    list_filter = ("store", "product__brand", "product__category")
    search_fields = ("store__name", "product__name", "product__sku")
    autocomplete_fields = ("store", "product")
    list_select_related = ("store", "product")


# ---------- Promos ----------
@admin.action(description="Activar promos seleccionadas (status → active)")
def make_active(modeladmin, request, queryset):
    count = queryset.update(status=FlashPromoStatus.ACTIVE)
    modeladmin.message_user(request, f"{count} promo(s) activadas.")

@admin.action(description="Finalizar promos seleccionadas (status → finished)")
def make_finished(modeladmin, request, queryset):
    count = queryset.update(status=FlashPromoStatus.FINISHED)
    modeladmin.message_user(request, f"{count} promo(s) finalizadas.")

@admin.register(FlashPromo)
class FlashPromoAdmin(admin.ModelAdmin):
    list_display = ("id", "store_product", "promo_price", "status", "starts_at", "ends_at", "is_active_now")
    list_filter = ("status", "starts_at", "ends_at", "store_product__store")
    search_fields = (
        "store_product__store__name",
        "store_product__product__name",
        "store_product__product__sku",
    )
    autocomplete_fields = ("store_product",)
    date_hierarchy = "starts_at"
    ordering = ("-starts_at",)
    list_select_related = ("store_product", "store_product__store", "store_product__product")
    actions = [make_active, make_finished]

    @admin.display(boolean=True, description="Activa ahora")
    def is_active_now(self, obj: FlashPromo):
        now = timezone.now()
        return obj.status == FlashPromoStatus.ACTIVE and obj.starts_at <= now <= obj.ends_at


# ---------- Notificaciones ----------
@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "promo", "sent_date", "sent_at")
    list_filter = ("sent_date",)
    search_fields = ("user__username", "user__email", "promo__store_product__product__name")
    autocomplete_fields = ("user", "promo")
    date_hierarchy = "sent_at"
    list_select_related = ("user", "promo")


# ---------- Reservas ----------
@admin.action(description="Marcar reservas seleccionadas como expiradas (restaura stock)")
def expire_reservations(modeladmin, request, queryset):

    to_expire = queryset.select_related("store_product").filter(status=ReservationStatus.HOLD)
    count = 0
    for res in to_expire:
        sp = res.store_product
        sp.stock = sp.stock + 1
        sp.save(update_fields=["stock"])
        res.status = ReservationStatus.EXPIRED
        res.save(update_fields=["status"])
        count += 1
    modeladmin.message_user(request, f"{count} reserva(s) expiradas y stock restaurado.")

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("token", "user", "store_product", "status", "expires_at", "created_at")
    list_filter = ("status", "expires_at", "created_at", "store_product__store")
    search_fields = ("token", "user__username", "store_product__product__name", "store_product__store__name")
    autocomplete_fields = ("user", "promo", "store_product")
    readonly_fields = ("token", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("user", "store_product", "store_product__store", "store_product__product")
    actions = [expire_reservations]
