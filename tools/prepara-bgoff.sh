#!/bin/bash
# Costruisce l'immagine Boot Guard off da un dump nuovo con MFIT 18.0 e la controlla.
# Non scrive sul chip: alla fine stampa i comandi per farlo.
# Uso: prepara-bgoff.sh /percorso/mfit.exe dump.bin cartella-nuova
set -eu
MFIT_SHA=ae2aa2bb97e2fa6ccc666ea46af270ca95a034a6a2af7c98b8249c11849d66d0   # 18.0.10.2285
QUI="$(cd "$(dirname "$0")" && pwd)"
[ $# -eq 3 ] || { sed -n '2,4p' "$0"; exit 2; }
MFIT="$(realpath "$1")"; DUMP="$(realpath "$2")"; DEST="$3"
ferma() { echo; echo "FERMO: $*" >&2; echo "NON scrivere niente." >&2; exit 1; }
passo() { echo; echo "### $*"; }
mfit() { "$QUI/mfit-sandbox.sh" "$MFIT" "$1" "${@:2}" 2>&1 | grep -v '^Fontconfig error' >> "$DEST/mfit.log"; }

passo "Controllo degli ingressi"
[ "$(sha256sum < "$MFIT" | cut -c1-64)" = "$MFIT_SHA" ] || ferma "$MFIT non e' MFIT 18.0.10.2285 (hash diverso)"
echo "MFIT 18.0.10.2285, hash corretto"
[ "$(stat -c %s "$DUMP")" = 33554432 ] || ferma "il dump non e' di 32 MiB"
[ ! -e "$DEST" ] || ferma "$DEST esiste gia': serve una cartella nuova"
mkdir -p "$DEST"; DEST="$(realpath "$DEST")"
cp "$DUMP" "$DEST/dump.bin"
echo "dump $(sha256sum < "$DEST/dump.bin" | cut -c1-16)... copiato in $DEST"

passo "Configurazione estratta dal dump"
mfit "$DEST" --decompose dump.bin --saveconfig config.xml
[ -f "$DEST/config.xml" ] || ferma "MFIT non ha generato config.xml, vedi $DEST/mfit.log"
PROF="$(grep -o '<BtGuardProfileConfig value="[^"]*"' "$DEST/config.xml" || true)"
[ "$PROF" = '<BtGuardProfileConfig value="Debug Profile"' ] || ferma "profilo nel dump inatteso: ${PROF:-assente}"
sed 's/<BtGuardProfileConfig value="Debug Profile"/<BtGuardProfileConfig value="Boot Guard Disabled"/' \
  "$DEST/config.xml" > "$DEST/config-bg.xml"
[ "$(diff "$DEST/config.xml" "$DEST/config-bg.xml" | grep -c '^>')" = 1 ] || ferma "config-bg.xml cambia piu' di una riga"
echo "profilo nel dump: Debug Profile; config-bg.xml cambia solo quello"

passo "Build con MFIT 18.0"
mfit "$DEST" --decompose dump.bin --loadconfig config.xml --build out-controllo.bin
mfit "$DEST" --decompose dump.bin --loadconfig config-bg.xml --build out-bgoff.bin
for f in out-controllo.bin out-bgoff.bin; do
  grep -q "'$f' image built successfully" "$DEST/mfit.log" && [ -f "$DEST/$f" ] || ferma "build di $f fallita, vedi $DEST/mfit.log"
done
echo "out-controllo.bin e out-bgoff.bin costruite"

passo "Ricomposizione di out-bgoff.bin"
mkdir "$DEST/ricomposta"; cp "$DEST/out-bgoff.bin" "$DEST/ricomposta/"
mfit "$DEST/ricomposta" --decompose out-bgoff.bin --saveconfig config.xml
[ -f "$DEST/ricomposta/config.xml" ] || ferma "ricomposizione fallita, vedi $DEST/mfit.log"
grep -q 'MFIT version used to build the image: 18.0.10.2285' "$DEST/mfit.log" || ferma "l'immagine non risulta costruita con la 18.0.10.2285"
echo "fatto"

passo "Controlli"
python3 -I "$QUI/verifica-bgoff.py" "$DEST/dump.bin" "$DEST/out-controllo.bin" "$DEST/out-bgoff.bin" \
  "$DEST/config.xml" "$DEST/ricomposta/config.xml" | tee "$DEST/verifica.log"
[ "${PIPESTATUS[0]}" = 0 ] || ferma "controlli falliti, vedi $DEST/verifica.log"

(cd "$DEST" && sha256sum dump.bin out-controllo.bin out-bgoff.bin > SHA256SUMS)
passo "Pronta: $DEST/out-bgoff.bin"
cat <<EOF
sha256 $(cut -c1-64 < "$DEST/SHA256SUMS" | sed -n 3p)

Prima di scrivere: recupero col T48 provato (guida, sezione 11, passo 2).

Col T48, a macchina spenta: immagine intera out-bgoff.bin.
Dall'interno, solo la regione ME, subito dopo il dump:
  sudo modprobe -r spi_intel_pci spi_intel
  sudo flashrom -p internal --ifd -i me -N -w $DEST/out-bgoff.bin
Poi spegnere, staccare l'alimentatore per 30 secondi e riaccendere.
EOF
