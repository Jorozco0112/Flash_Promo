# Flash Promos API

API de ejemplo para un **Marketplace con Promociones Flash**. Permite que tiendas creen productos y promociones con activación programada; segmenta usuarios por **comportamiento** (nuevo/frecuente) y **distancia ≤ 2 km** a la tienda, envía notificaciones (antispam por día), y maneja **reserva (hold) por 60s** con confirmación/cancelación seguras frente a concurrencia.

## Stack

- **Django + DRF** (API)
- **PostgreSQL + PostGIS** (geodatos y distancias)
- **Redis** (broker/result backend Celery; opcional para holds de alta escala)
- **Celery (worker + beat)** (activación y notificaciones)
- **drf-spectacular** (OpenAPI + Swagger/Redoc)
- **pgAdmin** (UI para DB)

---

## Arquitectura (resumen)

- Modelos principales:
  - `Product`, `Store(geom)`, `StoreProduct(stock, base_price)`
  - `FlashPromo(store_product, starts_at, ends_at, status)`
  - `Profile(user, geom, is_new_user, is_frequent)`
  - `NotificationLog(user, promo, sent_date)` → antispam “1 por día por promo”
  - `Reservation(promo, store_product, user, status, token, expires_at)`
- Reglas:
  - Una promo se **crea** como `scheduled` y **Celery Beat** la activa cuando `now() ∈ [starts_at, ends_at]`.
  - Notificaciones a usuarios elegibles (comportamiento + distancia ≤ 2 km).
  - Apartado (hold) por 60s: **confirmar** o **expirar/cancelar** restaura stock atómicamente.
- Endpoints:
  - CRUD: `Product`, `Store`, `StoreProduct`
  - Flujo: listar promos activas, crear promo programada, reservar/confirmar/cancelar

---

## Requisitos

- Docker y Docker Compose
- (Opcional local) Python 3.12+ si vas a ejecutar comandos fuera de contenedor

---

## Variables de Entorno

Copia `.env.example` → `.env` y ajusta:

```env
# Postgres
POSTGRES_DB=""
POSTGRES_USER=""
POSTGRES_PASSWORD=""
POSTGRES_HOST=""
POSTGRES_PORT=""

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Django
SECRET_KEY=""
DEBUG=""
ALLOWED_HOSTS=""
TIME_ZONE=America/Bogota
WEB_PORT=""

# Celery
CELERY_BROKER_URL=""
CELERY_RESULT_BACKEND=""

# pgAdmin
PGADMIN_EMAIL=""
PGADMIN_PASSWORD=""
PGADMIN_PORT=""
```

---

## Cómo correr con Docker

```bash
# 1) Construir imágenes
docker compose build --no-cache

# 2) Levantar stack
docker compose up -d

# 3) Aplicar migraciones (incluye extensión PostGIS vía migración)
docker compose exec api python manage.py migrate

# 4) (Opcional) crear superusuario para /admin
docker compose exec api python manage.py createsuperuser
```

Ver logs:
```bash
docker compose logs -f api worker beat postgres redis
```

**Swagger / Redoc / Schema**

- Swagger UI: `http://localhost:8000/api/docs/`
- OpenAPI JSON: `http://localhost:8000/api/schema/`

---

## Autenticación

**BasicAuth** en pruebas:

```python
REST_FRAMEWORK = {
  "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.BasicAuthentication"],
  "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
```

En Swagger, pulsa **Authorize → basicAuth** y usa tu usuario/clave.

---

## Endpoints

### CRUDs

- **Products**
  - `GET /api/products/`
  - `POST /api/products/`
  - `GET /api/products/{id}/`
  - `PUT/PATCH /api/products/{id}/`
  - `DELETE /api/products/{id}/`

- **Stores**
  - `GET /api/stores/`
  - `POST /api/stores/`
  - `GET /api/stores/{id}/`
  - `PUT/PATCH /api/stores/{id}/`
  - `DELETE /api/stores/{id}/`

- **StoreProducts**
  - `GET /api/store-products/`
  - `POST /api/store-products/`
  - `GET /api/store-products/{id}/`
  - `PUT/PATCH /api/store-products/{id}/`
  - `DELETE /api/store-products/{id}/`

### Promos

- **Crear Flash Promo (scheduled)**
  - `POST /admin/promos/`

- **Listar Promos activas**
  - `GET /promos/active`

### Carrito / Reservas

- **Reservar (HOLD)**
  - `POST /cart/reserve`
- **Confirmar compra**
  - `PUT /cart/checkout`
- **Cancelar / Expirar**
  - `PUT /cart/cancel`

---

## Tareas de Celery

- `activate_and_notify_promos`: activa promos programadas y finaliza vencidas.
- `notify_active_promos`: notifica usuarios elegibles.
- `notify_promo`: agrupa por promo.
- `send_push_batch`: registra `NotificationLog`. simula el envio de notificacion al usuario.

---

## Datos de prueba

```bash
docker compose exec api python manage.py migrate
```
Existe archivo de migracion para datos iniciales.
Crea usuario, tienda, producto, store_product y promo.

---

## Consideraciones de distancia

Usa `PointField(geography=True)` y filtro:

```python
geom__distance_lte=(profile.geom, D(km=2))
```

---

## Troubleshooting

- No ves promos → revisa estado, horario, perfil y distancia.
- No hay `NotificationLog` → revisa tareas de Celery.
- Errores Celery import → revisa `INSTALLED_APPS` y `celery.py`.

---

## Licencia

MIT
