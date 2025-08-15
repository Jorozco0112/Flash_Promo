from django.db import models


MINIMUM_DISTANCE = 2000 # Represent the  2km distance


class FlashPromoStatus(models.TextChoices):
    """This class contain the different
    status that a promo can have"""

    SCHEDULED = ("SCHEDULED", "Agendado")
    ACTIVE = ("ACTIVE", "Activa")
    FINISHED = ("FINISHED", "Finalizado")


class ReservationStatus(models.TextChoices):
    """This class contain all the status
    for reservation entity"""

    HOLD = ("HOLD", "Retenido")
    CONFIRMED = ("CONFIRMED", "Confirmado")
    CANCELED = ("CANCELED", "Cancelado")
    EXPIRED = ("EXPIRED", "Expirado")
