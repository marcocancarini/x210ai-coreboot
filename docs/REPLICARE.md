# Come replicare

Provato su CachyOS, kernel 7.3.1, GCC 16.2, Python 3.14. Commit esatti in [`config/versioni.txt`](../config/versioni.txt).

## Build di coreboot

```sh
tools/build.sh /percorso/di/lavoro/coreboot
```

Lo script clona il fork al commit previsto, applica le patch, compila la toolchain e costruisce `build/coreboot.rom`. Include le due correzioni servite qui:

- `nasm-3.02` da `www.coreboot.org/releases/crossgcc-sources/`, perché nasm.us non rispondeva. `buildgcc` ne verifica il checksum.
- Pulizia del clone annidato di `openssl` in `libspdm`, dove `fuzz/corpora` blocca il checkout dei sottomoduli.

Lo script raccoglie i passaggi fatti a mano, ma non è stato rieseguito da zero. La toolchain richiede dipendenze standard: `gcc`, `g++`, `make`, `bison`, `flex`, `m4`, `nasm`, `iasl`, ncurses, zlib, uuid, openssl, gmp, mpfr.

`EDK2_TAG_OR_REV` punta a un branch, `origin/uefipayload_2605`, che può muoversi: il commit usato è in `versioni.txt`. L'hash della ROM può quindi cambiare tra una build e l'altra.

**Controllo sull'immagine:**

```sh
build/cbfstool build/coreboot.rom layout -w
build/cbfstool build/coreboot.rom extract -n fallback/dsdt.aml -f dsdt.aml
iasl -d dsdt.aml && grep -E 'Method \((_Q06|_Q07|INCB|DECB)' dsdt.dsl
```

## Ottenere MFIT

MFIT è software Intel non pubblico. Serve per scomporre e ricostruire l'immagine, e non scrive sul chip.

- **Via ufficiale:** account Intel Premier, documento #821989, pacchetto CSME MTL-H/U 18.0.5.2141. Alcuni utenti non lo trovano.
- **Via usata qui:** `CSME System Tools 18.1.18.2749.rar`, da una fonte non Intel, quindi l'unica prova di autenticità è la firma.

| File | SHA-256 |
|---|---|
| Archivio `.rar` | `7e80dcdafd4cd4f70d7edacfc8e112dce9698feb4344144f7a1380f9009f79f1` |
| `MFIT/Windows64/mfit.exe` | `5cdb093dd8f515ec8b8e4fa69985e0c40b35d193bb4d026a48c7f359ed2ea06e` |

```sh
python3 -m venv venv && venv/bin/pip install signify
venv/bin/python -I tools/verifica-firma.py mfit.exe
```

**Controllo:** esito `OK` e firmatario `CN=Intel Corporation`. Usare solo `mfit.exe`: il `mfit` per Linux del pacchetto non è firmato, e gli altri file non sono stati verificati. L'archivio è passato per le mani di un tecnico, come mostra il `fit.log` rimasto dentro: la firma protegge solo il singolo eseguibile.

## Immagine con Boot Guard disattivato

```sh
mkdir lavoro && cp fresh1.bin lavoro/
tools/mfit-sandbox.sh mfit.exe lavoro --decompose fresh1.bin --saveconfig config.xml
cp lavoro/config.xml lavoro/config-bg.xml
sed -i 's/<BtGuardProfileConfig value="Debug Profile"/<BtGuardProfileConfig value="Boot Guard Disabled"/' lavoro/config-bg.xml
tools/mfit-sandbox.sh mfit.exe lavoro --decompose fresh1.bin --loadconfig config-bg.xml --build out-bgoff.bin
python3 -I tools/confronta-regioni.py lavoro/fresh1.bin lavoro/out-bgoff.bin
python3 -I tools/partizioni-me.py lavoro/fresh1.bin lavoro/out-controllo.bin lavoro/out-bgoff.bin
```

Per `partizioni-me.py` serve anche un'immagine di controllo: stessa build con `config.xml` non modificata, in uscita `out-controllo.bin`.

**Controllo:** riscomporre `out-bgoff.bin` deve mostrare `BtGuardProfileConfig value="Boot Guard Disabled"`.

## Strumenti

| Script | A cosa serve |
|---|---|
| `lettura.sh` | Stato del ME, Boot Guard, VBT, due letture del chip |
| `build.sh` | Build completa di coreboot |
| `mfit-sandbox.sh` | MFIT sotto wine, senza rete, con accesso alla sola cartella di lavoro |
| `verifica-firma.py` | Firma Authenticode e firmatario |
| `descriptor.py` | Regioni e permessi del flash descriptor |
| `analisi-bootguard.py` | Catena di Boot Guard da un dump e stato del ME, senza stampare dati della macchina |
| `confronta-regioni.py` | Differenze tra due immagini, regione per regione |
| `partizioni-me.py` | Partizioni del ME e blocchi cambiati |
| `vbt-info.py` | Controllo di un VBT |
| `acpi-tpm2.py` | Tipo di TPM dalla tabella ACPI, da un `acpidump` del BIOS originale |
