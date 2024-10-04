# Aplicación Python con FastAPI en Docker

Este proyecto contiene una aplicación Python que utiliza FastAPI y se ejecuta en un contenedor Docker.

## Requisitos

- Docker
- Docker Compose (opcional, pero recomendado)

## Estructura del Dockerfile

El Dockerfile está configurado para:

1. Usar Python 3.10 como base
2. Instalar las dependencias del proyecto desde `requirements.txt`
3. Instalar Google Chrome para funcionalidades que puedan requerirlo
4. Exponer el puerto 5002 para la aplicación FastAPI

## Cómo usar

### Construir la imagen

```bash
docker build -t fastapi-selenium .
```

### Ejecutar el contenedor

```bash
docker run -d -p 5002:5002 fastapi-selenium
```
