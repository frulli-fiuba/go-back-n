# TP 1 - Redes

**Correr el server:**

```bash
cd ./src && python3 start-server.py -v -s ../assets
```

**Descargar desde el servidor:**

```bash
cd ./src && python3 download.py -v -d ../assets/recibido-desde-servidor.png -n upload-test.png
```

**Correr upload:**

```bash
cd ./src && python3 upload.py -v -s ../assets/upload-test.png -n recibido-desde-upload.png
```