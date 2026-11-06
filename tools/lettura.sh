#!/bin/bash
# Solo lettura: non scrive sul chip. Uso: sudo bash lettura.sh [cartella]
set -u
UTENTE="${SUDO_USER:-$USER}"
OUT="${1:-/home/$UTENTE/x210ai-coreboot/backup}"
mkdir -p "$OUT"; cd "$OUT" || exit 1
LOG="$OUT/lettura-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee "$LOG") 2>&1
echo "### ME status (90000255 = manufacturing mode)"; setpci -s 00:16.0 0x40.l
echo "### MSR 0x13A (Boot Guard)"; modprobe msr; python3 -I -c "
import os,struct
f=os.open('/dev/cpu/0/msr',os.O_RDONLY); print(hex(struct.unpack('<Q',os.pread(f,8,0x13a))[0]))"
echo "### VBT"; i=0; for f in /sys/kernel/debug/dri/*/i915_vbt; do cat "$f" > "vbt-stock-$i.bin"; i=$((i+1)); done
echo "### Driver SPI scollegato"; modprobe -r spi_intel_pci spi_intel
echo "### Probe"; flashrom -p internal --flash-name
for n in 1 2; do echo "### Lettura $n"; flashrom -p internal -r "fresh$n.bin"; done
echo "### Protezioni"; flashrom -p internal --wp-status
echo "### Driver SPI ricollegato"; modprobe spi_intel_pci
sha256sum fresh1.bin fresh2.bin
chown -R "$UTENTE:$UTENTE" "$OUT"
echo "### Fine, log in $LOG"
