#!/bin/bash
# Esegue mfit.exe sotto wine in bwrap: senza rete, vede solo la cartella di lavoro.
# Il prefisso wine sta nel /tmp del sandbox, nuovo a ogni avvio: un prefisso salvato
# a metà fa fallire le esecuzioni successive (errore _Py_HashRandomization_Init).
# Uso: mfit-sandbox.sh /percorso/mfit.exe /cartella/lavoro <argomenti di mfit>
set -eu
MFIT="$(realpath "$1")"; LAVORO="$(realpath "$2")"; shift 2
exec bwrap --unshare-all --die-with-parent --new-session \
  --ro-bind /usr /usr --symlink usr/bin /bin --symlink usr/lib /lib --symlink usr/lib /lib64 \
  --ro-bind /etc/ld.so.cache /etc/ld.so.cache --proc /proc --dev /dev --tmpfs /tmp \
  --ro-bind "$MFIT" /app/mfit.exe --bind "$LAVORO" /work/job \
  --unsetenv DISPLAY --unsetenv WAYLAND_DISPLAY --unsetenv DBUS_SESSION_BUS_ADDRESS \
  --setenv HOME /tmp/home --setenv WINEPREFIX /tmp/wine --setenv WINEDEBUG -all \
  --setenv WINEDLLOVERRIDES 'mscoree,mshtml=' --chdir /work/job \
  wine /app/mfit.exe "$@"
