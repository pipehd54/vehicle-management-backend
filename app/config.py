from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta al archivo .env en la raíz del proyecto,
# independiente del directorio desde donde se ejecute la aplicación.
_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    """
    Configuración central de la aplicación.

    Pydantic-settings lee automáticamente las variables desde el archivo .env
    y las valida con tipos estrictos al iniciar. Si alguna variable obligatoria
    falta o tiene un tipo incorrecto, la aplicación falla al arrancar con un
    mensaje de error claro, antes de atender cualquier petición.
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        # Las variables POSTGRES_* del .env son para Docker Compose, no para Python.
        # 'ignore' evita que pydantic-settings falle al encontrar variables no declaradas.
        extra="ignore",
    )

    # --- Base de datos ---
    DATABASE_URL: str

    # --- Seguridad JWT ---
    # SecretStr es un tipo especial de Pydantic: nunca imprime el valor
    # real en logs ni en representaciones de texto. Para leer el valor
    # hay que llamar explícitamente a .get_secret_value().
    SECRET_KEY: SecretStr

    # Literal restringe el algoritmo a una lista blanca explícita.
    # Evita que alguien configure ALGORITHM=none (ataque histórico en JWT).
    ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"

    # gt=0: el token debe durar al menos 1 minuto.
    # le=10080: máximo 7 días (7 * 24 * 60).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0, le=10080)


# Instancia única compartida por toda la aplicación.
# Se crea una sola vez al importar el módulo; si la configuración
# es inválida, el error ocurre aquí, en el arranque.
settings = Settings()
