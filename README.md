# Trabajo práctico N°1

Este trabajo práctico implementa una arquitectura **cliente-servidor** para la transferencia de archivos utilizando los protocolos **Stop-and-Wait** y **Go-Back-N**.  
El entorno de pruebas se ejecuta sobre **Mininet**, lo que permite simular una red con distintos niveles de pérdida y retardo.

---

## Requisitos previos

Antes de ejecutar el proyecto, asegurate de tener instalado lo siguiente:

- **Python 3.8+**
- **Mininet** (`pip install mininet`)
- **Wireshark** (opcional, para visualización de tráfico)

---

## Ejecución manual (sin Mininet)

Podés ejecutar los scripts de manera directa para probar la funcionalidad básica del cliente y servidor, siempre dentro de la carpeta `/src`.

### 1. Iniciar el servidor

Desde una terminal:
```bash
python3 start-server.py -v -s ./assets -H 127.0.0.1
```

Donde:
- `-v` activa el modo verboso (opcional).
- `-s` indica la carpeta donde se encuentran los archivos disponibles para descargar y enviar.
- `-H` define la dirección IP del servidor (por defecto, `127.0.0.1`).

### 2. Descargar un archivo desde el cliente

Desde otra terminal:
```bash
python3 download.py -v -d ../assets/recibido-desde-servidor.png -n upload-test.png -H 10.0.0.1
```

Parámetros:
- `-v` activa el modo verboso (opcional).
- `-d`: nombre y ruta de donde será ubicado el archivo a descargar.
- `-n`: nombre del archivo que el servidor debe enviar.
- `-H`: IP del servidor.

### 3. Subir un archivo al servidor

Desde el cliente:
```bash
python3 upload.py -v -s ../assets/upload-test.png -n recibido-desde-upload.png  -H 10.0.0.1
```

Parámetros:
- `-v` activa el modo verboso (opcional).
- `-s`: ruta del archivo que será enviado al servidor.
- `-n`: nombre del archivo que el servidor va a crear.
- `-H`: IP del servidor.

---

## Ejecución con Mininet (`topology.py`)

El archivo `topology.py` permite simular una red de tres hosts conectados a un switch con distintas condiciones de red.

### 🔹 Topología

- **h1** → Servidor (con 10% de pérdida configurada en el enlace)  
- **h2** y **h3** → Clientes sin pérdida de paquetes  

### Cómo ejecutarlo

1. Asegurate de estar en el directorio que contiene todos los archivos (`start-server.py`, `download.py`, `upload.py`, `topology.py` y la carpeta `assets`).

2. Ejecutá el script de topología con permisos de administrador:
   ```bash
   sudo python3 topology.py
   ```

3. Automáticamente se abrirán terminales para cada host:
   - En **h1**, se iniciará **Wireshark** y el **servidor** (`start-server.py`) escuchando en la IP `10.0.0.1`.
   - En **h2** y **h3**, podrás ejecutar los clientes manualmente con los comandos:
     ```bash
     python3 download.py -v -d ../assets/recibido-desde-servidor.png -n upload-test.png -H 10.0.0.1
     ```
     o
     ```bash
     python3 upload.py -v -s ../assets/upload-test.png -n recibido-desde-upload.png  -H 10.0.0.1
     ```

4. Para finalizar la simulación, escribí en la consola de Mininet:
   ```
   exit
   ```
