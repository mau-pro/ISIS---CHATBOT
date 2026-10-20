#!/usr/bin/env bash
# Instala I-SIS en un servidor Ubuntu (Oracle Cloud u otro). Se ejecuta DENTRO de la carpeta
# del paquete, con la dirección pública del servidor:
#     bash instalar_servidor.sh http://123.45.67.89
# Es seguro repetirlo: no pisa la contraseña de la base ni los datos ya guardados.
set -euo pipefail
PUBLIC_URL="${1:?Falta la dirección pública, ej: bash instalar_servidor.sh http://123.45.67.89}"
PAQUETE="$(cd "$(dirname "$0")" && pwd)"
DESTINO="$HOME/asistente-universitario"
D="sudo docker"

echo "== 1/6 Docker =="
if ! command -v docker >/dev/null 2>&1; then curl -fsSL https://get.docker.com | sudo sh; fi
sudo systemctl enable --now docker >/dev/null 2>&1 || true

echo "== 2/6 Cortafuegos del servidor: abrir puertos 80 y 443 =="
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent >/dev/null 2>&1 || true
for p in 80 443; do
  sudo iptables -C INPUT -p tcp --dport "$p" -j ACCEPT 2>/dev/null || sudo iptables -I INPUT 1 -p tcp --dport "$p" -j ACCEPT
done
sudo netfilter-persistent save >/dev/null 2>&1 || true

echo "== 3/6 Código y configuración =="
mkdir -p "$DESTINO"
tar xzf "$PAQUETE/proyecto.tar.gz" -C "$DESTINO"
cp "$PAQUETE/backend.env" "$DESTINO/backend/.env"
if [ -f "$DESTINO/.env" ]; then
  sed -i "s|^PUBLIC_URL=.*|PUBLIC_URL=$PUBLIC_URL|" "$DESTINO/.env"
else
  CLAVE=$(head -c 96 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)
  printf 'POSTGRES_PASSWORD=%s\nPUBLIC_URL=%s\n' "$CLAVE" "$PUBLIC_URL" > "$DESTINO/.env"
fi
cd "$DESTINO"

echo "== 4/6 Base de datos: encender y restaurar tus datos =="
$D compose up -d db
for i in $(seq 1 40); do
  [ "$($D inspect -f '{{.State.Health.Status}}' "$($D compose ps -q db)")" = "healthy" ] && break
  sleep 3
done
if [ -f "$PAQUETE/asistente.dump" ]; then
  $D compose cp "$PAQUETE/asistente.dump" db:/tmp/asistente.dump
  $D compose exec -T db pg_restore -U isis -d asistente --clean --if-exists --no-owner /tmp/asistente.dump || true
fi

echo "== 5/6 Construir y encender el sistema (la primera vez tarda 10 a 25 minutos) =="
$D compose up -d --build
for i in $(seq 1 90); do
  [ "$($D inspect -f '{{.State.Health.Status}}' "$($D compose ps -q backend)")" = "healthy" ] && break
  sleep 4
done

echo "== 6/6 Índice de búsqueda =="
if [ -d "$PAQUETE/chroma_data" ]; then
  $D compose cp "$PAQUETE/chroma_data/." backend:/app/chroma_data/
  $D compose restart backend >/dev/null
fi

echo
echo "== Verificación =="
$D compose ps --format "table {{.Service}}\t{{.Status}}"
$D compose exec -T db psql -U isis -d asistente -t -A -c "select (select count(*) from users) || ' usuarios, ' || (select count(*) from documents) || ' documentos, ' || (select count(*) from document_files) || ' archivos'"
echo "Listo. Abrí:  $PUBLIC_URL"
