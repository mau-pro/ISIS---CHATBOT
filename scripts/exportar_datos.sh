#!/usr/bin/env bash
# Prepara el PAQUETE para subir al servidor. Se ejecuta en tu PC (Git Bash), con Docker
# encendido y el sistema funcionando:   bash scripts/exportar_datos.sh
# Crea despliegue/paquete-servidor.tar.gz con: código (último commit), base de datos
# (cuentas, historial y archivos), índice de búsqueda y backend.env (con una JWT nueva).
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
export PATH="/c/Users/$USERNAME/AppData/Local/Programs/DockerDesktop/resources/bin:$PATH"

if [ -n "$(git status --porcelain)" ]; then
  echo "Hay cambios sin commitear: hacé 'git commit' primero (el paquete usa el último commit)."; exit 1
fi

OUT=despliegue/paquete
rm -rf despliegue && mkdir -p "$OUT"

echo "1/5 Respaldo de PostgreSQL (cuentas, historial, documentos y sus archivos)"
docker compose exec -T db sh -c 'pg_dump -U isis -Fc asistente > /tmp/asistente.dump'
docker compose cp db:/tmp/asistente.dump "$OUT/asistente.dump"

echo "2/5 Índice de búsqueda (se detiene el backend un momento para copiarlo sano)"
docker compose stop backend >/dev/null
docker compose cp backend:/app/chroma_data "$OUT/chroma_data"
docker compose start backend >/dev/null

echo "3/5 Código del último commit"
git archive --format=tar.gz -o "$OUT/proyecto.tar.gz" HEAD

echo "4/5 Claves del backend, con una JWT_SECRET_KEY nueva y larga"
NUEVA=$(head -c 96 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 64)
grep -v -E '^(JWT_SECRET_KEY|DATABASE_URL)=' backend/.env > "$OUT/backend.env" || true
printf 'JWT_SECRET_KEY=%s\n' "$NUEVA" >> "$OUT/backend.env"

cp scripts/instalar_servidor.sh "$OUT/"
echo "5/5 Empaquetando"
tar czf despliegue/paquete-servidor.tar.gz -C despliegue paquete
echo "Listo: despliegue/paquete-servidor.tar.gz ($(du -h despliegue/paquete-servidor.tar.gz | cut -f1))"
