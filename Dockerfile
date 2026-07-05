FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear un usuario sin privilegios para ejecutar la aplicación.
# Si hay una brecha de seguridad en la app, el atacante no tendrá
# acceso de root al sistema de archivos del contenedor.
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
