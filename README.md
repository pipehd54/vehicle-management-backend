# Vehicle Management Backend

![CI](https://github.com/pipehd54/vehicle-management-backend/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![Ruff](https://img.shields.io/badge/code%20style-ruff-261230)
![License](https://img.shields.io/badge/license-MIT-green)

API REST para apoyar la gestión básica de un taller mecánico: vehículos,
mantenimientos y usuarios con autenticación JWT y control de acceso por roles
(RBAC).

Proyecto personal de portafolio, desarrollado como estudiante de Ingeniería de
Sistemas. El objetivo es construir una API backend con las herramientas
habituales del ecosistema Python, manteniendo una estructura simple, tipada y
fácil de extender.

- **Frontend en producción (Vercel):** [vehicle-management-frontend-ruby.vercel.app](https://vehicle-management-frontend-ruby.vercel.app/)
- **API en producción (Railway):** [vehicle-management-backend-production-e9f4.up.railway.app](https://vehicle-management-backend-production-e9f4.up.railway.app)
- **Documentación interactiva:** `/docs` (deshabilitada en producción)

---

## Funcionalidades

- Registro e inicio de sesión con **JWT** y contraseñas cifradas con **bcrypt**.
- Las cuentas registradas nacen **inactivas** y un administrador las activa; el
  registro no revela si un correo ya existe.
- **RBAC**: mecánico (crear, consultar y actualizar) y administrador (además,
  eliminar y activar cuentas).
- CRUD de vehículos y de sus mantenimientos, con paginación y filtros.
- **Motor de mantenimiento**: cálculo del próximo servicio según el manual del taller.
- Límite de intentos de login por IP y por cuenta, con soporte para proxies inversos.
- Health check de la API y de la base de datos.
## Stack

| Capa | Tecnología |
| --- | --- |
| API | FastAPI 0.137, Uvicorn |
| Datos | SQLAlchemy 2.0 (async) + asyncpg + PostgreSQL 16 |
| Validación | Pydantic v2 + pydantic-settings |
| Seguridad | PyJWT, bcrypt |
| Migraciones | Alembic |
| Pruebas | pytest, pytest-asyncio, httpx, pytest-cov |
| Calidad | Ruff (linter + formateador), mypy |
| Despliegue | Docker, Docker Compose, Railway |

## Inicio rápido

```bash
git clone https://github.com/pipehd54/vehicle-management-backend.git
cd vehicle-management-backend
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                # Windows: Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # genera la SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000` y la documentación en
`http://localhost:8000/docs`.

Con Docker el esquema se actualiza solo: Compose aplica las migraciones antes
de levantar la API.

```bash
cp .env.example .env    # y genera una SECRET_KEY real
docker compose up --build
```

## Estructura

```text
.
├── app/
│   ├── main.py             # Punto de entrada: middlewares, lifespan, routers
│   ├── configuracion.py    # Variables de entorno validadas al arrancar
│   ├── base_datos.py       # Motor asíncrono y sesiones
│   ├── modelos.py          # Modelos SQLAlchemy
│   ├── esquemas.py         # Schemas de Pydantic (entrada/salida)
│   ├── enums.py            # Rol, estado de mantenimiento y tipo de vehículo
│   ├── seguridad.py        # bcrypt, emisión y validación de JWT
│   ├── dependencias.py     # Dependencias de autorización (RBAC)
│   ├── limitador.py        # Límite de intentos por IP y por cuenta
│   ├── errores.py          # Errores HTTP reutilizables
│   ├── repositorio.py      # Consultas compartidas por los routers
│   ├── cli.py              # Utilidades de administración (crear-admin)
│   ├── servicios/          # Lógica de negocio pura (sin HTTP ni base de datos)
│   │   └── programa_mantenimiento.py
│   └── routers/            # Endpoints por recurso
├── alembic/                # Migraciones
├── tests/{unit,api}/       # Pruebas puras y de endpoints
├── pyproject.toml          # Dependencias y configuración de herramientas
├── Dockerfile
└── docker-compose.yml
```

## Endpoints

| Método | Endpoint | Descripción | Acceso |
| --- | --- | --- | --- |
| `GET` | `/` | Mensaje de bienvenida | Público |
| `GET` | `/health` | Estado de la API y de la base de datos | Público |
| `POST` | `/usuarios/` | Registra una cuenta (mecánico, inactiva) | Público (limitado) |
| `POST` | `/usuarios/login` | Devuelve un token JWT | Público (limitado) |
| `GET` | `/usuarios/me` | Datos del usuario autenticado | JWT |
| `POST` | `/usuarios/me/cambiar-password` | Cambia la contraseña propia | JWT |
| `GET` | `/usuarios/pendientes` | Cuentas pendientes de activación | Solo admin |
| `PATCH` | `/usuarios/{id}/activar` | Activa una cuenta | Solo admin |
| `PATCH` | `/usuarios/{id}/desactivar` | Desactiva una cuenta y le corta el acceso | Solo admin |
| `GET` | `/vehiculos/` | Lista vehículos paginados | JWT |
| `GET` | `/vehiculos/{id}` | Consulta un vehículo | JWT |
| `POST` | `/vehiculos/` | Crea un vehículo | JWT |
| `PATCH` o `PUT` | `/vehiculos/{id}` | Actualiza un vehículo | JWT |
| `DELETE` | `/vehiculos/{id}` | Elimina un vehículo y sus mantenimientos | Solo admin |
| `GET` | `/vehiculos/{id}/proximo-mantenimiento` | Próximo servicio recomendado | JWT |
| `GET` | `/mantenimientos/` | Lista mantenimientos (filtro por vehículo) | JWT |
| `GET` | `/mantenimientos/{id}` | Consulta un mantenimiento | JWT |
| `POST` | `/mantenimientos/` | Crea un mantenimiento | JWT |
| `PATCH` o `PUT` | `/mantenimientos/{id}` | Actualiza un mantenimiento | JWT |
| `DELETE` | `/mantenimientos/{id}` | Elimina un mantenimiento | Solo admin |

Paginación: `skip` (por defecto 0) y `limit` (por defecto 20, máximo 100).
Filtro: `GET /mantenimientos/?vehiculo_id=1`.

`PUT` y `PATCH` se comportan igual: **solo se modifican los campos enviados**,
el resto conserva su valor. Así, actualizar solo la marca de un vehículo no
reinicia su odómetro a cero ni borra el presupuesto de un mantenimiento.

## Administración

El registro público solo crea cuentas de mecánico, y nacen inactivas: hace
falta un administrador para activarlas. El primero se crea con la herramienta
de línea de comandos, sin tocar la base de datos a mano:

```bash
python -m app.cli crear-admin --email admin@taller.com
# La contraseña se solicita de forma oculta si no se pasa con --password.
```

## Variables de entorno

| Variable | Obligatoria | Por defecto | Descripción |
| --- | --- | --- | --- |
| `DATABASE_URL` | Sí | — | URL de PostgreSQL. Se normaliza a `postgresql+asyncpg://` |
| `SECRET_KEY` | Sí | — | Clave de firma JWT (mínimo 32 caracteres) |
| `ALGORITHM` | No | `HS256` | Algoritmo JWT (lista blanca: HS256/384/512) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Vigencia del token (1 minuto – 7 días) |
| `CORS_ORIGINS` | No | `localhost:3000,5173` | Orígenes del frontend, separados por comas |
| `APP_ENV` | No | `desarrollo` | `desarrollo` \| `produccion` \| `pruebas` |
| `TRUSTED_PROXY_IPS` | No | vacío | Proxies de confianza para leer `X-Forwarded-For` |

La aplicación **falla al arrancar** si falta una variable obligatoria, si la
clave es demasiado corta o si todavía es el valor de ejemplo: es preferible
que el despliegue falle de forma visible a que quede una clave pública.

## Decisiones de diseño

- **JWT sin estado y rol siempre desde la base de datos**: no hay lista de
  revocación, pero cada petición relee `is_active` y el `rol`, así que un
  cambio de estado o de rol surte efecto inmediato.
- **Contraseñas con bcrypt** y límite de 72 bytes, validado en el schema.
- **Comparación de tiempo constante en el login**: si el correo no existe se
  compara contra un hash señuelo, para que el tiempo de respuesta no permita
  enumerar cuentas.
- **Solo se cuentan los intentos fallidos** al aplicar el límite: el tráfico
  legítimo no agota la cuota por IP detrás de un proxy.
- **La lógica de mantenimiento es una función pura** en
  `app/servicios/programa_mantenimiento.py`: sin FastAPI ni base de datos, se
  testea en milisegundos y se puede reutilizar desde un script.
- **Datos validados en la entrada**: enumeraciones en lugar de cadenas
  sueltas para rol, estado y tipo de vehículo (la API responde 422 ante un
  estado desconocido) y actualizaciones parciales, para que modificar un
  campo no destruya los demás.
- **El primer administrador se crea con una herramienta**, no con SQL: la API
  no expone ningún endpoint que conceda el rol de administrador.
- **Herramientas declaradas en `pyproject.toml`**: una sola fuente de verdad
  para dependencias, linter, formateador, pruebas y cobertura.

## Reglas del motor de mantenimiento

El próximo servicio se calcula con el **mayor** entre el nivel deducido del
kilometraje y el nivel que indica el historial de revisiones completadas:

| Kilometraje | Nivel | Objetivo |
| --- | --- | --- |
| < 500 km | 1 | 500 km |
| < 3 000 km | 2 | 3 000 km |
| < 6 000 km | 3 | 6 000 km |
| < 9 000 km | 4 | 9 000 km |
| < 12 000 km | 5 | 12 000 km |
| ≥ 12 000 km | 5 + tramos de 3 000 km | 15 000 km, 18 000 km, … |

La fecha sugerida se cuenta desde el último servicio completado o, si no
existe, desde la fecha de compra del vehículo.

## Pruebas

```bash
pytest -q                                  # usa SQLite en memoria
pytest -q --cov=app --cov-report=term-missing
```

Por defecto las pruebas usan SQLite asíncrono en memoria. Definiendo
`TEST_DATABASE_URL` se ejecutan contra PostgreSQL, que es lo que hace CI.

## Seguridad

- Cabeceras de seguridad (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy` y HSTS bajo HTTPS).
- CORS con lista explícita de orígenes; el comodín `*` está prohibido.
- La documentación interactiva se desactiva en `APP_ENV=produccion`.
- Contenedor sin privilegios y usuario no root.
- El limitador de intentos vive en memoria y es por proceso: con varias
  réplicas hay que aplicarlo en un gateway.

## Licencia

MIT. Consulta [LICENSE](LICENSE).
