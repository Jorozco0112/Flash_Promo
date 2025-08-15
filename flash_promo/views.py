from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema

from .permissions import IsAdminOrReadOnly
from .models import FlashPromo, Reservation, Product, StoreProduct, Store
from .constants import FlashPromoStatus
from .serializers import (
    PromoListSerializer,
    ReservationCreateSerializer,
    ReservationResponseSerializer,
    ReservationTokenSerializer,
    ReservationStatusSerializer,
    ProductSerializer,
    StoreProductSerializer,
    StoreSerializer,
    FlashPromoCreateSerializer
)
from .queries import active_promos_for_profile, user_is_eligible_for_promo, get_profile_by_user
from .services import (
    hold_store_product_db,
    confirm_reservation,
    cancel_or_expire_reservation,
)



class ActivePromosView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={status.HTTP_200_OK: PromoListSerializer}
    )
    def get(self, request):
        profile = get_profile_by_user(user=request.user)
        active_promos_qs = active_promos_for_profile(profile)
        print("active_promos:", active_promos_qs, flush=True)
        data = PromoListSerializer(active_promos_qs, many=True).data

        return Response(data, status=status.HTTP_200_OK)


class ReservePromoView(APIView):
    """
    POST: Create the reservation for 60s if the profile meet both conditions
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ReservationCreateSerializer,
        responses={status.HTTP_201_CREATED: ReservationResponseSerializer}
    )
    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        promo = get_object_or_404(
            FlashPromo.objects.select_related("store_product", "store_product__store"),
            pk=serializer.validated_data["promo_id"]
        )
        # valida ventana y estado
        if not (
            promo.status == FlashPromoStatus.ACTIVE and
            promo.starts_at <= now() <= promo.ends_at
        ):
            return Response({"detail": "Promo not activated"}, status=status.HTTP_400_BAD_REQUEST)

        profile = get_profile_by_user(user=request.user)
        if not user_is_eligible_for_promo(profile, promo):
            return Response(
                {"detail": "User does not meet both condition"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            hold_reservation = hold_store_product_db(request.user, promo)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        reservation_serialized = ReservationResponseSerializer(
            {
                "reservation_token": hold_reservation.token,
                "expires_at": hold_reservation.expires_at
            }
        ).data
        return Response(reservation_serialized, status=status.HTTP_201_CREATED)


class ConfirmReservationView(APIView):
    """
    PUT: Confirm a reservation. reservation_token is required
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ReservationTokenSerializer,
        responses={status.HTTP_200_OK: ReservationStatusSerializer}
    )
    def put(self, request):
        serializer = ReservationTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirmed_reservation = confirm_reservation(
                serializer.validated_data["reservation_token"],
                request.user
            )
        except Reservation.DoesNotExist:
            return Response({"detail": "Reserva no encontrada"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ReservationStatusSerializer(confirmed_reservation).data,
            status=status.HTTP_200_OK
        )

class CancelReservationView(APIView):
    """
    PUT: cancela una reserva activa (o la marca expirada y devuelve stock).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ReservationTokenSerializer,
        responses={status.HTTP_200_OK: ReservationStatusSerializer}
    )
    def put(self, request):
        serializer = ReservationTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            canceled_reservation = Reservation.objects.get(
                token=serializer.validated_data["reservation_token"],
                user=request.user
            )
        except Reservation.DoesNotExist:
            return Response({"detail": "Reserva no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        reservation_serialized = cancel_or_expire_reservation(canceled_reservation)
        return Response(
            ReservationStatusSerializer(reservation_serialized).data,
            status=status.HTTP_200_OK
        )


class FlashPromoCreateView(APIView):
    """
    Create an scheduled flash promo.
    Then celery beat update to ACTIVATE.
    """
    permission_classes = [IsAdminOrReadOnly]

    @extend_schema(
        request=FlashPromoCreateSerializer,
        responses={status.HTTP_201_CREATED: FlashPromoCreateSerializer},
        summary="Create flash promo"
    )
    def post(self, request):
        ser = FlashPromoCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        promo = ser.save()

        out = FlashPromoCreateSerializer(promo).data
        return Response(out, status=status.HTTP_201_CREATED)


# ---- Products ----
@extend_schema(tags=["Products"])
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("id")
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ("name", "sku", "brand", "category")
    filterset_fields = ("brand", "category")


# ---- Stores ----
@extend_schema(tags=["Stores"])
class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all().order_by("id")
    serializer_class = StoreSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ("name",)


# ---- StoreProducts ----
@extend_schema(tags=["StoreProducts"])
class StoreProductViewSet(viewsets.ModelViewSet):
    queryset = (
        StoreProduct.objects
        .select_related("store", "product")
        .all().order_by("id")
    )
    serializer_class = StoreProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ("store__name", "product__name", "product__sku")
    filterset_fields = ("store", "product")
