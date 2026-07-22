# Vehicle Management Backend

![CI](https://github.com/pipehd54/vehicle-management-backend/actions/workflows/ci.yml/badge.svg)

API REST para apoyar la gestión básica de un taller mecánico. Permite registrar usuarios, autenticar con JWT y administrar vehículos junto con sus mantenimientos mediante un control de acceso basado en roles (RBAC).

Este es un proyecto personal de portafolio desarrollado como estudiante de Ingeniería de Sistemas. Su objetivo es practicar la construcción de una API backend con herramientas habituales del ecosistema Python, manteniendo una estructura simple y fácil de entender.

- **🌐 Frontend en producción (Vercel):** [https://vehicle-management-frontend-ruby.vercel.app/](https://vehicle-management-frontend-ruby.vercel.app/)
- **🚀 API en producción (Railway):** [https://vehicle-management-backend-production-e9f4.up.railway.app](https://vehicle-management-backend-production-e9f4.up.railway.app/)
- **📖 Documentación interactiva:** [https://vehicle-management-backend-production-e9f4.up.railway.app/docs](https://vehicle-management-backend-production-e9f4.up.railway.app/docs)

---

## Funcionalidades

- Registro e inicio de sesión de usuarios.
- Autenticación mediante tokens JWT.
- Contraseñas almacenadas con hash seguro de bcrypt.
- Control de Acceso Basado en Roles (RBAC):
  - **Mecánico:** Crear/Consultar vehículos y crear/actualizar mantenimientos.
  - **Administrador:** Además de las funciones anteriores, tiene permisos exclusivos para eliminar registros.
- CRUD de vehículos.
- CRUD de mantenimientos asociados a un vehículo.
- Paginación en los listados de vehículos y mantenimientos.
- Health check para comprobar la conexión con la base de datos.
- Migraciones de base de datos con Alembic.
- Pruebas automatizadas con SQLite en memoria, sin modificar PostgreSQL.
- Contenedores para API y PostgreSQL mediante Docker Compose.

## Tecnologías

- Python 3.12
- FastAPI
- SQLAlchemy Async
- PostgreSQL
- Alembic
- Pydantic v2
- PyJWT y bcrypt
- Pytest, pytest-asyncio, HTTPX y aiosqlite
- Docker y Docker Compose

## Estructura del proyecto

```text
.
├── alembic/              # Migraciones de la base de datos
├── app/
│   ├── routers/          # Endpoints de usuarios, vehículos y mantenimientos
│   ├── config.py         # Configuración por variables de entorno
│   ├── database.py       # Motor y sesiones asíncronas
│   ├── depends.py        # Dependencias de seguridad y roles (RBAC)
│   ├── models.py         # Modelos de SQLAlchemy
│   ├── schemas.py        # Modelos de validación Pydantic
│   └── security.py       # Hash de contraseñas y JWT
├── tests/                # Pruebas automatizadas
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Requisitos

- Python 3.12 o superior
- PostgreSQL 16, si se ejecuta sin Docker
- Docker Desktop y Docker Compose, si se ejecuta con contenedores

## Variables de entorno

Crea un archivo llamado `.env` en la raíz del proyecto. No debe subirse al repositorio.

Para ejecutar la aplicación localmente con PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://taller_user:tu_password@localhost:5432/taller_db
SECRET_KEY=una_clave_larga_y_secreta_de_al_menos_32_caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://vehicle-management-frontend-ruby.vercel.app
```

Para Docker Compose, usa el nombre del servicio `db` como host y define además la contraseña de PostgreSQL:

```env
POSTGRES_DB=taller_db
POSTGRES_USER=taller_user
POSTGRES_PASSWORD=tu_password
DATABASE_URL=postgresql+asyncpg://taller_user:tu_password@db:5432/taller_db
SECRET_KEY=una_clave_larga_y_secreta_de_al_menos_32_caracteres
```

`CORS_ORIGINS` admite varios orígenes separados por comas, por ejemplo: `http://localhost:3000,http://localhost:5173,https://vehicle-management-frontend-ruby.vercel.app`.

## Ejecutar con Docker

1. Crea el archivo `.env` con las variables del apartado anterior.
2. Construye e inicia los servicios:

```powershell
docker compose up --build
```

3. En otra terminal, aplica las migraciones:

```powershell
docker compose exec api alembic upgrade head
```

La API estará disponible en `http://localhost:8000` y la documentación interactiva en `http://localhost:8000/docs`.

Para detener los servicios:

```powershell
docker compose down
```

## Ejecutar localmente

1. Crea y activa un entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

2. Instala las dependencias:

```powershell
pip install -r requirements.txt
```

3. Crea la base de datos en PostgreSQL y configura el archivo `.env`.

4. Aplica las migraciones:

```powershell
alembic upgrade head
```

5. Inicia la API:

```powershell
uvicorn app.main:app --reload
```

## Endpoints principales

| Método | Endpoint | Descripción | Acceso |
| --- | --- | --- | --- |
| `GET` | `/` | Mensaje de bienvenida | Público |
| `GET` | `/health` | Estado de la API y la base de datos | Público |
| `POST` | `/usuarios/` | Registra un usuario (mecanico/administrador) | Público |
| `POST` | `/usuarios/login` | Devuelve un token JWT | Público |
| `GET` | `/vehiculos/` | Lista vehículos paginados | Público |
| `GET` | `/vehiculos/{vehiculo_id}` | Consulta un vehículo | Público |
| `POST` | `/vehiculos/` | Crea un vehículo | JWT |
| `PUT` | `/vehiculos/{vehiculo_id}` | Actualiza un vehículo | JWT |
| `DELETE` | `/vehiculos/{vehiculo_id}` | Elimina un vehículo y sus mantenimientos | JWT (Solo Admin) |
| `GET` | `/mantenimientos/` | Lista mantenimientos paginados y filtrables | Público |
| `GET` | `/mantenimientos/{mantenimiento_id}` | Consulta un mantenimiento | Público |
| `POST` | `/mantenimientos/` | Crea un mantenimiento | JWT |
| `PUT` | `/mantenimientos/{mantenimiento_id}` | Actualiza un mantenimiento | JWT |
| `DELETE` | `/mantenimientos/{mantenimiento_id}` | Elimina un mantenimiento | JWT (Solo Admin) |

### Paginación y filtro

Los listados aceptan los parámetros `skip` y `limit`:

```text
GET /vehiculos/?skip=0&limit=20
GET /mantenimientos/?skip=0&limit=20
GET /mantenimientos/?vehiculo_id=1&skip=0&limit=20
```

`skip` empieza en `0`. `limit` tiene un valor por defecto de `20` y acepta un máximo de `100`.

## Ejemplos de uso

Registrar un usuario:

```json
{
  "email": "mecanico@example.com",
  "password": "password123",
  "rol": "mecanico"
}
```

Crear un vehículo:

```json
{
  "placa": "XYZ-123",
  "marca": "Toyota",
  "modelo": "Corolla"
}
```

Crear un mantenimiento:

```json
{
  "vehiculo_id": 1,
  "descripcion": "Cambio de aceite y revisión general",
  "estado": "pendiente",
  "costo_estimado": 120000
}
```

En los endpoints protegidos, incluye el token obtenido en el login:

```text
Authorization: Bearer <access_token>
```

## Pruebas

Las pruebas usan SQLite asíncrono en memoria. No se conectan ni modifican tu instancia de PostgreSQL.

```powershell
pytest -q
```

La suite cubre autenticación, autorización sin token, control de acceso RBAC por rol de administrador vs mecánico, CRUD de vehículos, CRUD de mantenimientos, paginación, filtros y borrado en cascada.
