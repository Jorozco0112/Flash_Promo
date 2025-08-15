"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from flash_promo.views import (
    ActivePromosView,
    ReservePromoView,
    ConfirmReservationView,
    CancelReservationView,
    StoreViewSet,
    StoreProductViewSet,
    ProductViewSet,
    FlashPromoCreateView
)

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"stores", StoreViewSet, basename="store")
router.register(r"store-products", StoreProductViewSet, basename="storeproduct")

urlpatterns = [
    path("admin/", admin.site.urls),

    # --- API ---
    path("promos", FlashPromoCreateView.as_view()),
    path("promos/active", ActivePromosView.as_view()),
    path("cart/reserve", ReservePromoView.as_view()),
    path("cart/checkout", ConfirmReservationView.as_view()),
    path("cart/cancel", CancelReservationView.as_view()),
    path("api/", include(router.urls)),

    # --- OpenAPI / Swagger ---
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(
        url_name='schema'
    ), name='swagger-ui'),
]
