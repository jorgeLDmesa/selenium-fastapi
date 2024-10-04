# Usa una imagen base de Python 3.10
FROM python:3.10

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de requisitos primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Instala Chrome y las dependencias necesarias
RUN apt-get update && apt-get install -y wget unzip && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -f -y && \
    rm google-chrome-stable_current_amd64.deb && \
    apt-get clean

# Copia el resto del código de la aplicación
COPY . .

# Expone el puerto en el que se ejecutará FastAPI
EXPOSE 5002

# Comando para ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5002"]