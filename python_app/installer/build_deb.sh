#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "dpkg-deb não encontrado. Instale o pacote dpkg-dev." >&2
  exit 1
fi
if ! command -v fakeroot >/dev/null 2>&1; then
  echo "fakeroot não encontrado. Instale fakeroot." >&2
  exit 1
fi

BUILD_DIR="$ROOT_DIR/build/deb"
PKG_ROOT="$BUILD_DIR/cadastro-clientes-python"
DEB_DIR="$PKG_ROOT/opt/cadastro-clientes-python"

rm -rf "$BUILD_DIR"
mkdir -p "$DEB_DIR"

if [ ! -f "$ROOT_DIR/dist/app" ]; then
  echo "Binário Linux não encontrado em dist/app. Gere com PyInstaller primeiro." >&2
  exit 1
fi

cp "$ROOT_DIR/dist/app" "$DEB_DIR/"
cp -r "$ROOT_DIR/data" "$DEB_DIR/"
if [ -d "$ROOT_DIR/server/static" ]; then
  mkdir -p "$DEB_DIR/server/static"
  cp -r "$ROOT_DIR/server/static/"* "$DEB_DIR/server/static/"
fi

mkdir -p "$PKG_ROOT/DEBIAN"
cat > "$PKG_ROOT/DEBIAN/control" <<'EOF'
Package: cadastro-clientes-python
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6 (>= 2.29)
Maintainer: Your Name <you@example.com>
Description: Cadastro Clientes local application em Python/Flask empacotado como binário.
EOF

cat > "$PKG_ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
ln -sf /opt/cadastro-clientes-python/app /usr/local/bin/cadastro-clientes-python
EOF
chmod 755 "$PKG_ROOT/DEBIAN/postinst"

OUTPUT_DEB="$ROOT_DIR/dist/cadastro-clientes-python_1.0.0_amd64.deb"
fakeroot dpkg-deb --build "$PKG_ROOT" "$OUTPUT_DEB"

echo "DEB gerado em: $OUTPUT_DEB"