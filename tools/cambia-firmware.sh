#!/bin/sh
# Passa da una ROM all'altra (Heads <-> edk2) riscrivendo solo la regione WP_RO
# della FMAP: FMAP e CBFS. Restano com'erano SMMSTORE (variabili UEFI, voci di
# avvio di Windows, chiavi Secure Boot), RW_MRC_CACHE, ME e descriptor.
#
# Uso, da root:  cambia-firmware.sh ROM [cartella-backup]
# Funziona da CachyOS (flashrom) e dalla shell di recupero di Heads (flashprog).
# Per le prove senza chip: PROGRAMMATORE="dummy:emulate=VARIABLE_SIZE,size=33554432,image=FILE"
set -eu
ROM="$1"
BACKUP="${2:-$(dirname "$ROM")}"
QUI="$(cd "$(dirname "$0")" && pwd)"
ELENCO="$QUI/../config/rom-conosciute.txt"
PROGRAMMATORE="${PROGRAMMATORE:-internal}"

ferma() { echo "FERMO: $*" >&2; exit 1; }

[ -f "$ROM" ] || ferma "ROM non trovata: $ROM"
[ "$(wc -c < "$ROM")" -eq 33554432 ] || ferma "la ROM non e' di 32 MiB"
SHA="$(sha256sum "$ROM" | cut -c1-64)"
NOME="$(grep "^$SHA " "$ELENCO" 2>/dev/null | cut -d' ' -f2- || true)"
[ -n "$NOME" ] || ferma "hash $SHA non in $ELENCO: aggiungerlo solo per una ROM verificata"
echo "ROM: $NOME"

if command -v flashprog >/dev/null; then F=flashprog
elif command -v flashrom >/dev/null; then F=flashrom
else ferma "ne' flashprog ne' flashrom"; fi

DRIVER=0
if [ "$PROGRAMMATORE" = internal ] && grep -q '^spi_intel' /proc/modules 2>/dev/null; then
  modprobe -r spi_intel_pci spi_intel && DRIVER=1
fi
rimetti() { [ "$DRIVER" = 1 ] && modprobe spi_intel_pci || true; }
trap rimetti EXIT

COPIA="$BACKUP/chip-prima-del-cambio-$(date +%Y%m%d-%H%M%S).bin"
echo "Copia completa del chip in $COPIA"
$F -p "$PROGRAMMATORE" -r "$COPIA" >/dev/null || ferma "lettura del chip fallita, nulla e' stato scritto"
[ "$(wc -c < "$COPIA")" -eq 33554432 ] || ferma "copia del chip incompleta, nulla e' stato scritto"

if cmp -s "$COPIA" "$ROM" 2>/dev/null; then echo "Il chip contiene gia' questa ROM per intero."; exit 0; fi

echo "Scrittura della sola regione WP_RO (FMAP + CBFS)..."
$F -p "$PROGRAMMATORE" --fmap-file "$ROM" -i WP_RO --noverify-all -w "$ROM" \
  || ferma "scrittura fallita: NON spegnere, rilanciare lo script. Copia del chip in $COPIA"
echo
echo "Fatto: $NOME. Spegnere del tutto e riaccendere."
