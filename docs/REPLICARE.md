# Come replicare

Provato su CachyOS, kernel 7.3.1, GCC 16.2, Python 3.14. Commit esatti in [`config/versioni.txt`](../config/versioni.txt).

## Build di coreboot

```sh
tools/build.sh /percorso/di/lavoro/coreboot
```

Lo script clona il fork al commit previsto, applica le patch, compila la toolchain e costruisce `build/coreboot.rom`. Include le due correzioni servite qui:

- `nasm-3.02` da `www.coreboot.org/releases/crossgcc-sources/`, perché nasm.us non rispondeva. `buildgcc` ne verifica il checksum.
- Pulizia del clone annidato di `openssl` in `libspdm`, dove `fuzz/corpora` blocca il checkout dei sottomoduli.
- Microcode portato al tag `microcode-20260925` (`06-aa-04` revisione `0x2b`). Il submodule va aggiunto all'indice con `git add`: altrimenti il Makefile di coreboot, alla voce "Updating git submodules", lo riporta al commit fissato dal fork e la ROM esce di nuovo con `0x28`.

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

**MFIT 18.0.10.2285**, trovata il 2026-11-08 in tre archivi, `mfit.part1.rar`, `part2` e `part3`, da una fonte non Intel. Contengono solo `mfit.exe`.

| File | SHA-256 |
|---|---|
| `mfit.part1.rar` | `f2e44dd33796fe22f48f4a0c8ee1188b05590ea2286091abaf60ac0dae3d314f` |
| `mfit.part2.rar` | `3fd0050956e91fa40d79c5a3eccdf9dd0ccac2e38ef73ed470d468005a19824a` |
| `mfit.part3.rar` | `0fa7ebb2af14699b37dff3c992d888484945874d890772bc8b9076a199697b0d` |
| `mfit.exe` 18.0.10.2285 | `ae2aa2bb97e2fa6ccc666ea46af270ca95a034a6a2af7c98b8249c11849d66d0` |

Firma `OK`, `CN=Intel Corporation`, certificato Sectigo valido dal 2024-03-13 al 2025-03-13, controfirma del 2024-07-14.

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

```sh
python3 -I tools/uep.py lavoro/fresh1.bin lavoro/out-controllo.bin lavoro/out-bgoff.bin
```

Atteso per `out-bgoff.bin`: slot A valido, CRC `a779` corretto, profilo `18`, flag `00`, slot B vuoto.

### Confronto con MFIT 18.0

Non ancora eseguito. Si ripetono gli stessi passi in una cartella nuova, estraendo la configurazione con la 18.0 e senza riusare quella della 18.1:

```sh
M18=/percorso/di/mfit-18.0.10.2285.exe
mkdir lavoro-18.0 && cp fresh1.bin lavoro-18.0/
tools/mfit-sandbox.sh $M18 lavoro-18.0 --decompose fresh1.bin --saveconfig config.xml
cp lavoro-18.0/config.xml lavoro-18.0/config-bg.xml
sed -i 's/<BtGuardProfileConfig value="Debug Profile"/<BtGuardProfileConfig value="Boot Guard Disabled"/' lavoro-18.0/config-bg.xml
tools/mfit-sandbox.sh $M18 lavoro-18.0 --decompose fresh1.bin --loadconfig config.xml --build out-controllo.bin
tools/mfit-sandbox.sh $M18 lavoro-18.0 --decompose fresh1.bin --loadconfig config-bg.xml --build out-bgoff.bin
python3 -I tools/partizioni-me.py lavoro-18.0/fresh1.bin lavoro-18.0/out-controllo.bin lavoro-18.0/out-bgoff.bin
python3 -I tools/uep.py lavoro-18.0/out-bgoff.bin
python3 -I tools/confronta-regioni.py lavoro/out-bgoff.bin lavoro-18.0/out-bgoff.bin
```

Come leggere il risultato: differenze solo in CDMD, FITC e nei metadati di build vogliono dire che le due versioni sono equivalenti. Differenze in UEP o nei moduli del firmware vogliono dire che conviene usare l'immagine della 18.0.

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
| `uep.py` | I due slot di UEP: firma, CRC, profilo di Boot Guard, flag `+0x58` e stato atteso dopo il primo avvio |
| `vbt-info.py` | Controllo di un VBT |
| `acpi-tpm2.py` | Tipo di TPM dalla tabella ACPI, da un `acpidump` del BIOS originale |
