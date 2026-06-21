# 🏍️ Garage API - Sistema de Gestión Vehicular

Un backend robusto y de alto rendimiento diseñado para administrar el registro, inventario y mantenimiento de vehículos en un taller mecánico. Desarrollado bajo una arquitectura asíncrona moderna utilizando Python y FastAPI.

## 🚀 Características Principales

* **Arquitectura Asíncrona:** Operaciones de entrada/salida no bloqueantes para un máximo rendimiento.
* **Seguridad de Nivel Empresarial:** * Hasheo de contraseñas de mecánicos/administradores utilizando `Bcrypt`.
    * Protección de endpoints mediante tokens de acceso `JWT` (JSON Web Tokens).
* **Base de Datos Relacional:** Modelado de datos estructurado utilizando `PostgreSQL` y `SQLAlchemy`.
* **Control de Versiones (DB):** Gestión de migraciones seguras con `Alembic`.
* **Validación Estricta:** Filtrado y serialización de datos de entrada/salida usando esquemas de `Pydantic`.

## 🛠️ Stack Tecnológico

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **Lenguaje:** Python 3.10+
* **Base de Datos:** PostgreSQL
* **ORM:** SQLAlchemy (Async)
* **Migraciones:** Alembic
* **Seguridad:** PyJWT, Passlib[bcrypt]

## 📋 Estructura de Endpoints (API)

| Método | Endpoint             | Descripción                                      | Acceso |
| :---   | :---                 | :---                                             | :---   |
| `POST` | `/usuarios/login`    | Autenticación de mecánicos y generación de Token | Público|
| `GET`  | `/vehiculos/`        | Obtiene el listado de vehículos registrados      | Público|
| `POST` | `/vehiculos/`        | Registra un nuevo vehículo en el taller          | 🔒 JWT |
| `PUT`  | `/vehiculos/{id}`    | Actualiza los datos de un vehículo existente     | 🔒 JWT |
| `DELETE`| `/vehiculos/{id}`   | Elimina un vehículo del registro del taller      | 🔒 JWT |

### Ejemplo de Payload (POST `/vehiculos/`)
```json
{
  "placa": "XYZ-123",
  "marca": "Hero",
  "modelo": "Hunk 150 XTEC"
}
