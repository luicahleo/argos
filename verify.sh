#!/usr/bin/env bash
# Puerta de calidad local de ARGOS. Espeja exactamente lo que corre
# .github/workflows/ci.yml, para detectar fallos antes del push en vez de
# después, ya que develop/master ya no tienen branch protection ni PR.
set -Eeuo pipefail

verde() { printf '\033[32m[OK]\033[0m %s\n' "$1"; }
rojo() { printf '\033[31m[FALLO]\033[0m %s\n' "$1"; }

fallo() {
    rojo "$1"
    rojo 'La puerta de calidad no paso. Arregla el contenido, no el gate.'
    exit 1
}
trap 'fallo "Puerta de calidad interrumpida"' ERR

PYTHON=python3
command -v python3 >/dev/null 2>&1 || PYTHON=python

echo '== Sintaxis Python =='
"$PYTHON" -m compileall -q ARGOS runserver.py benchmark_lfw.py
verde 'Sintaxis Python'

echo '== Build Docker (argos:ci) =='
docker build --tag argos:ci . >/dev/null
verde 'Build Docker'

echo '== Tests =='
# MSYS_NO_PATHCONV evita que Git Bash en Windows reescriba las rutas estilo
# Unix (/app, /repo) como si fueran relativas a la instalacion de Git.
MSYS_NO_PATHCONV=1 docker run --rm \
    --volume "$(pwd):/repo:ro" \
    --workdir /app \
    argos:ci python -m unittest discover -s /repo/tests -p 'test_*.py' -v
verde 'Tests'

echo
verde 'Puerta de calidad: verde.'
