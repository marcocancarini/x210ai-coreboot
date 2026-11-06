#!/bin/bash
# Ricostruisce l'immagine: clone del fork, patch, toolchain, build.
# Uso: build.sh [cartella-destinazione]
set -eu
QUI="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$PWD/coreboot}"
FORK_COMMIT="$(sed -n 's/^fork_commit=//p' "$QUI/config/versioni.txt")"
[ -d "$DEST" ] || git clone --branch x210ai https://github.com/WheeledCord/coreboot-x210ai "$DEST"
cd "$DEST"
git checkout -q "$FORK_COMMIT"
git submodule update --init --checkout
git apply --check "$QUI"/patches/*.patch && git apply "$QUI"/patches/*.patch
# nasm.us puo' non rispondere: si usa il mirror di coreboot, buildgcc controlla il checksum.
[ -f util/crossgcc/tarballs/nasm-3.02.tar.bz2 ] || curl -sS --fail -o util/crossgcc/tarballs/nasm-3.02.tar.bz2 \
  https://www.coreboot.org/releases/crossgcc-sources/nasm-3.02.tar.bz2
env -u MAKEFLAGS /usr/bin/make crossgcc-i386 crossgcc-x64 CPUS="$(nproc)"
cp "$QUI/config/coreboot.config" .config
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
