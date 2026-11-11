#!/bin/bash
# Ricostruisce l'immagine: clone del fork, patch, toolchain, build.
# Uso: [VARIANTE=tpm] [SENZA_FIX_TB=1] build.sh [cartella-destinazione]
#   VARIANTE=tpm:   PTT acceso (patches/opzionale/0003) e config/coreboot-tpm.config
#   SENZA_FIX_TB=1: senza la patch Thunderbolt 0004, la ROM di ripiego
# Le quattro ROM di rom/: nessuna opzione (edk2-senza-tpm), SENZA_FIX_TB=1,
# VARIANTE=tpm (edk2-con-tpm), VARIANTE=tpm SENZA_FIX_TB=1.
set -eu
QUI="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$PWD/coreboot}"
FORK_COMMIT="$(sed -n 's/^fork_commit=//p' "$QUI/config/versioni.txt")"
[ -d "$DEST" ] || git clone --branch x210ai https://github.com/WheeledCord/coreboot-x210ai "$DEST"
cd "$DEST"
git checkout -q "$FORK_COMMIT"
git submodule update --init --checkout
# Microcode piu' recente del commit fissato dal fork (0x28 -> 0x2b per 06-aa-04).
# Va messo nell'indice, altrimenti il Makefile di coreboot riporta il submodule indietro.
UCODE_TAG="$(sed -n 's/^microcode_tag=//p' "$QUI/config/versioni.txt")"
git -C 3rdparty/intel-microcode fetch -q origin tag "$UCODE_TAG"
git -C 3rdparty/intel-microcode checkout -q "$UCODE_TAG"
git add 3rdparty/intel-microcode
PATCH=("$QUI"/patches/*.patch)
if [ "${SENZA_FIX_TB:-}" = 1 ]; then
  PATCH=("${PATCH[@]/*0004-x210ai-thunderbolt-rp1.patch}")
  PATCH=($(printf "%s\n" "${PATCH[@]}" | grep .))
fi
git apply --check "${PATCH[@]}" && git apply "${PATCH[@]}"
CONFIG="$QUI/config/coreboot.config"
if [ "${VARIANTE:-}" = tpm ]; then
  git apply "$QUI/patches/opzionale/0003-x210ai-tpm-ptt.patch"
  CONFIG="$QUI/config/coreboot-tpm.config"
fi
# nasm.us puo' non rispondere: si usa il mirror di coreboot, buildgcc controlla il checksum.
[ -f util/crossgcc/tarballs/nasm-3.02.tar.bz2 ] || curl -sS --fail -o util/crossgcc/tarballs/nasm-3.02.tar.bz2 \
  https://www.coreboot.org/releases/crossgcc-sources/nasm-3.02.tar.bz2
env -u MAKEFLAGS /usr/bin/make crossgcc-i386 crossgcc-x64 CPUS="$(nproc)"
cp "$CONFIG" .config
env -u MAKEFLAGS /usr/bin/make olddefconfig
if ! env -u MAKEFLAGS /usr/bin/make -j"$(nproc)"; then
  # Il clone annidato di openssl in libspdm lascia fuzz/corpora non tracciato.
  W=payloads/external/edk2/workspace/mrchromebox
  L=SecurityPkg/DeviceSecurity/SpdmLib/libspdm; O=$L/os_stub/openssllib/openssl
  C="$(git -C "$W/$L" ls-tree HEAD os_stub/openssllib/openssl | awk '{print $3}')"
  git -C "$W/$O" clean -ffdxq
  git -C "$W/$O" checkout -q -f "$C"
  git -C "$W" submodule update --init --checkout --recursive
  env -u MAKEFLAGS /usr/bin/make -j"$(nproc)"
fi
sha256sum build/coreboot.rom
