"""Configuración central de la aplicación.

Pydantic-settings lee automáticamente las variables desde el archivo .env
y las valida con tipos estrictos al iniciar. Si alguna variable obligatoria
falta o tiene un tipo incorrecto, la aplicación falla al arrancar con un
mensaje de error claro, antes de atender cualquier petición.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta al archivo .env en la raíz del proyecto,
# independiente del directorio desde donde se ejecute la aplicación.
_ENV_FILE = Path(__file__).parent.parent / ".env"

#: Entornos admitidos. En "produccion" la documentación interactiva se apaga.
Entorno = Literal["desarrollo", "produccion", "pruebas"]

#: Texto que delata una clave de ejemplo sin cambiar. Si aparece en el
#: SECRET_KEY, la aplicación se niega a arrancar.
_MARCADORES_DE_CLAVE_EJEMPLO = (
    "reemplaza",
    "cambia",
    "genera",
    "aleatoria",
    "ejemplo",
    "example",
    "changeme",
    "placeholder",
    "xxxx",
)


class Settings(BaseSettings):
    """Variables de entorno validadas de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        # Las variables POSTGRES_* del .env son para Docker Compose, no para Python.
        # 'ignore' evita que pydantic-settings falle al encontrar variables
        # que no estan declaradas (por ejemplo, las de Docker Compose).
        extra="ignore",
    )

    # --- Entorno ---
    APP_ENV: Entorno = "desarrollo"

    # --- Base de datos ---
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalizar_database_url(cls, v: str) -> str:
        """Normaliza las URLs de Railway al dialecto asyncpg.

        Acepta tanto `postgres://` como `postgresql://` y los convierte en
        `postgresql+asyncpg://`, que es el dialecto que usa la aplicacion.
        """
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # --- Seguridad JWT ---
    # SecretStr es un tipo especial de Pydantic: nunca imprime el valor
    # real en logs ni en representaciones de texto. Para leer el valor
    # hay que llamar explícitamente a .get_secret_value().
    # min_length=32 hace cumplir en código lo que exige el README:
    # una clave HMAC corta permitiría forjar JWT arbitrarios.
    SECRET_KEY: SecretStr = Field(min_length=32)

    @field_validator("SECRET_KEY")
    @classmethod
    def rechazar_clave_de_ejemplo(cls, v: SecretStr) -> SecretStr:
        """Impide desplegar con la clave de ejemplo del .env.example."""
        valor = v.get_secret_value().lower()
        if any(marcador in valor for marcador in _MARCADORES_DE_CLAVE_EJEMPLO):
            raise ValueError(
                "SECRET_KEY parece un valor de ejemplo. Genera una clave "
                "aleatoria antes de desplegar (por ejemplo con "
                '`python -c "import secrets; print(secrets.token_urlsafe(48))"`).'
            )
        return v

    # Literal restringe el algoritmo a una lista blanca explícita.
    # Evita que alguien configure ALGORITHM=none (ataque histórico en JWT).
    ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"

    # gt=0: el token debe durar al menos 1 minuto.
    # le=10080: máximo 7 días (7 * 24 * 60).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0, le=10080)

    # --- CORS ---
    # Orígenes permitidos para el cliente web. Se reciben separados por comas.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("CORS_ORIGINS")
    @classmethod
    def rechazar_origenes_globales(cls, v: str) -> str:
        """Rechaza el comodín: la API no debe servirse desde cualquier origen."""
        origenes = [origen.strip() for origen in v.split(",") if origen.strip()]
        if "*" in origenes:
            raise ValueError(
                "CORS_ORIGINS no admite '*'. Indica los orígenes concretos "
                "del frontend, separados por comas."
            )
        return v

    @property
    def cors_origins(self) -> list[str]:
        """Lista de orígenes permitidos, ya normalizada."""
        return [
            origen.strip() for origen in self.CORS_ORIGINS.split(",") if origen.strip()
        ]

    # --- Proxy inverso ---
    # Direcciones IP (o rangos CIDR) de los proxies de confianza. Solo si la
    # aplicación se ejecuta detrás de un proxy (Railway, Nginx, un balanceador)
    # conviene declarar aquí ese proxy: es lo que permite leer la IP real del
    # cliente en X-Forwarded-For. Vacío = no se confía en ninguna cabecera.
    TRUSTED_PROXY_IPS: str = ""

    @property
    def trusted_proxy_ips(self) -> set[str]:
        """Conjunto de direcciones IP de proxies de confianza."""
        return {
            direccion.strip()
            for direccion in self.TRUSTED_PROXY_IPS.split(",")
            if direccion.strip()
        }

    @property
    def documentacion_activada(self) -> bool:
        """En producción la documentación interactiva queda deshabilitada."""
        return self.APP_ENV != "produccion"


# Instancia única compartida por toda la aplicación.
# Se crea una sola vez al importar el módulo; si la configuración
# es inválida, el error ocurre aquí, en el arranque.
settings = Settings()
