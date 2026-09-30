#!/usr/bin/env bash
# Garante um Python com Playwright + Chromium em ~/.venvs/miners-reverse-branding e imprime o caminho do python.
# Uso: PY=$(bash setup.sh)
set -e
VENV="$HOME/.venvs/miners-reverse-branding"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV" >&2
fi
if ! "$VENV/bin/python" -c "import playwright" 2>/dev/null; then
  "$VENV/bin/pip" install -q playwright >&2
fi
# Instala o Chromium só se ainda não existir (o comando é idempotente, mas lento)
if ! ls "$HOME/Library/Caches/ms-playwright" "$HOME/.cache/ms-playwright" 2>/dev/null | grep -q chromium; then
  "$VENV/bin/python" -m playwright install chromium >&2
fi
echo "$VENV/bin/python"
