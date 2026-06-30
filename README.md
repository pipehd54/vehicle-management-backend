# Garage API - Sistema de Gestion de Taller

API backend simple para gestionar usuarios, vehiculos y mantenimientos de un taller mecanico.

El objetivo del proyecto es mostrar una base funcional de desarrollo backend con Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, autenticacion JWT y Docker.

## Caracteristicas

- Registro de usuarios.
- Login con JWT.
- Hash de contrasenas con Passlib y bcrypt.
- CRUD basico de vehiculos.
- CRUD basico de mantenimientos asociados a vehiculos.
- Base de datos PostgreSQL.
- Migraciones con Alembic.
- Dockerizacion con Docker Compose para levantar API y base de datos.

## Stack tecnologico

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy Async
- Alembic
- Pydantic
- PyJWT
- Docker
- Docker Compose

## Endpoints principales

| Metodo | Endpoint | Descripcion | Acceso |
| --- | --- | --- | --- |
| `POST` | `/usuarios/` | Registra un usuario | Publico |
| `POST` | `/usuarios/login` | Inicia sesion y devuelve un token JWT | Publico |
| `GET` | `/vehiculos/` | Lista los vehiculos registrados | Publico |
| `POST` | `/vehiculos/` | Registra un vehiculo | JWT |
| `PUT` | `/vehiculos/{vehiculo_id}` | Actualiza un vehiculo | JWT |
| `DELETE` | `/vehiculos/{vehiculo_id}` | Elimina un vehiculo | JWT |
| `GET` | `/mantenimientos/` | Lista mantenimientos | Publico |
| `GET` | `/mantenimientos/{mantenimiento_id}` | Obtiene un mantenimiento | Publico |
| `POST` | `/mantenimientos/` | Crea un mantenimiento | JWT |
| `PUT` | `/mantenimientos/{mantenimiento_id}` | Actualiza un mantenimiento | JWT |
| `DELETE` | `/mantenimientos/{mantenimiento_id}` | Elimina un mantenimiento | JWT |

## Ejecutar con Docker

Requisitos:

- Docker Desktop instalado y corriendo.
- Docker Compose disponible.

Levantar la API y PostgreSQL:

```powershell
docker compose up --build
```

La API quedara disponible en:

```text
http://localhost:8000
```

La documentacion interactiva de FastAPI estara en:

```text
http://localhost:8000/docs
```

En otra terminal, aplicar migraciones:

```powershell
docker compose exec api alembic upgrade head
```

Detener los contenedores:

```powershell
docker compose down
```

Detener los contenedores y eliminar el volumen de PostgreSQL:

```powershell
docker compose down -v
```

> Nota: `docker compose down -v` borra los datos guardados en la base de datos del contenedor.

## Variables de entorno en Docker

El archivo `docker-compose.yml` define variables de entorno de desarrollo para la API:

```yaml
DATABASE_URL: postgresql+asyncpg://taller_user:taller_password@db:5432/taller_db
SECRET_KEY: clave_de_desarrollo_para_docker
ALGORITHM: HS256
ACCESS_TOKEN_EXPIRE_MINUTES: 60
```

Dentro de Docker Compose, la API se conecta a PostgreSQL usando el nombre del servicio `db`.

## Ejemplos de payload

Crear usuario:

```json
{
  "email": "mecanico@example.com",
  "password": "password123"
}
```

Crear vehiculo:

```json
{
  "placa": "XYZ-123",
  "marca": "Toyota",
  "modelo": "Corolla"
}
```

Crear mantenimiento:

```json
{
  "vehiculo_id": 1,
  "descripcion": "Cambio de aceite y revision general",
  "estado": "pendiente",
  "costo_estimado": 120000
}
```

## Ejecutar sin Docker

Crear y activar un entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Configurar variables de entorno en `.env` tomando como referencia `.env.example`.

Aplicar migraciones:

```powershell
alembic upgrade head
```

Ejecutar la API:

```powershell
uvicorn app.main:app --reload
```
