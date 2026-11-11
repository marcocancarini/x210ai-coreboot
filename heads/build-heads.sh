#!/bin/bash
# Variante Heads SPERIMENTALE: prepara l'albero di Heads e lancia la build nel
# container ufficiale (docker_repro.sh). Non scrive sul chip.
# Uso: heads/build-heads.sh [cartella-heads]   (richiede Docker)
set -eu
QUI="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$PWD/heads}"
BOARD=x210ai-tpm2-sperimentale
val() { sed -n "s/^$1=//p" "$QUI/config/versioni.txt"; }
HEADS_COMMIT="$(val heads_commit)"
UCODE_COMMIT="$(val microcode_commit)"
UCODE_URL=https://raw.githubusercontent.com/intel/Intel-Linux-Processor-Microcode-Data-Files
# I tre file che il fork mette nella ROM (soc/intel/meteorlake/Makefile.mk), al tag microcode-20260925.
UCODE="c1295a2c7c38797e07fdcf28a07c11271909be295dd264e3adfcc221850d3712 06-aa-04
a1645454fcccbdc5e48279e544ad364b66ee229dea1dcbdbefefb64061a5b46c 06-b5-00
468e5b1f2b9b9b1af0b7a7ee63940e5a16a52813d57e770c424c9866df08f189 06-c6-02"

[ -d "$DEST" ] || git clone https://github.com/linuxboot/heads "$DEST"
cd "$DEST"
git fetch -q origin "$HEADS_COMMIT" 2>/dev/null || true
git checkout -q -f "$HEADS_COMMIT"

# Versione "x210ai" di coreboot in modules/coreboot
P="$QUI/heads/heads-modules-coreboot.patch"
git apply -R --check "$P" 2>/dev/null || git apply "$P"

# Scheda e configurazioni
mkdir -p "boards/$BOARD"
cp "$QUI/heads/$BOARD.config" "boards/$BOARD/$BOARD.config"
cp "$QUI/heads/coreboot-x210ai.config" config/coreboot-x210ai.config
cp "$QUI/heads/linux-x210ai.config" config/linux-x210ai.config

# Patch di coreboot, nell'ordine in cui si applicano: il TPM va dopo Thunderbolt.
rm -rf patches/coreboot-x210ai && mkdir -p patches/coreboot-x210ai
cp "$QUI/patches/0001-x210ai-luminosita.patch" patches/coreboot-x210ai/0001-x210ai-luminosita.patch
cp "$QUI/patches/0004-x210ai-thunderbolt-rp1.patch" patches/coreboot-x210ai/0002-x210ai-thunderbolt-rp1.patch
cp "$QUI/patches/opzionale/0003-x210ai-tpm-ptt.patch" patches/coreboot-x210ai/0003-x210ai-tpm-ptt.patch
# cbmem va nell'initrd e si compila con musl, che non include <endian.h> da solo:
# stessa correzione che Heads usa per il fork MrChromebox.
cp patches/coreboot-mrchromebox-26.03/0001-util-cbmem-Add-endian.h-include-for-musl-compat.patch \
  patches/coreboot-x210ai/0004-cbmem-endian-musl.patch

# Microcode 0x2b come file esterni: Heads clona il fork senza sottomoduli e
# il Makefile di coreboot riporterebbe intel-microcode al commit del fork (0x28).
mkdir -p blobs/x210ai
echo "$UCODE" | while read -r sha f; do
  if [ ! -f "blobs/x210ai/$f" ] || [ "$(sha256sum < "blobs/x210ai/$f" | cut -c1-64)" != "$sha" ]; then
    curl -sSfL -o "blobs/x210ai/$f" "$UCODE_URL/$UCODE_COMMIT/intel-ucode/$f"
    [ "$(sha256sum < "blobs/x210ai/$f" | cut -c1-64)" = "$sha" ] || { echo "hash di $f errato" >&2; exit 1; }
  fi
done
echo "Albero di Heads pronto in $DEST"

command -v docker >/dev/null || { echo "Docker non trovato: installarlo e rilanciare." >&2; exit 1; }
# docker_repro.sh usa docker run -ti: senza terminale serve script(1) per avere una PTY.
nel_container() {
  if [ -t 0 ]; then ./docker_repro.sh "$@"
  else script -qefc "HEADS_DISABLE_USB=1 ./docker_repro.sh $*" /dev/null; fi
}
# Il container gira come root: alla fine si restituiscono i file all'utente.
ESITO=0
nel_container make BOARD="$BOARD" || ESITO=$?
nel_container chown -R "$(id -u):$(id -g)" build crossgcc install packages 2>/dev/null || true
[ "$ESITO" = 0 ] || { echo "Build di Heads fallita ($ESITO)" >&2; exit "$ESITO"; }

echo
ls -la "build/x86/$BOARD/"*.rom
sha256sum "build/x86/$BOARD/"*.rom
cat <<EOF

ROM SPERIMENTALE, mai avviata. Scrivere solo la regione BIOS, e solo dopo un
primo avvio riuscito della build edk2 (docs/HEADS.md):
  sudo flashrom -p internal --ifd -i bios -N -w <rom>
EOF
