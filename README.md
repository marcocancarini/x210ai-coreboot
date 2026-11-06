# Coreboot su 51NB X210AI

Installazione di coreboot con UEFI (edk2) su X210AI Core Ultra 7 165H: patch, configurazione, strumenti e procedura.

> **Stato al 2026-11-06: nulla è stato scritto sul chip.** L'immagine compila, ma non è mai stata avviata su questa scheda. Prima di scrivere serve un recupero funzionante col T48.

Parte dal port di Fionn Cassidy, [WheeledCord/coreboot-x210ai](https://github.com/WheeledCord/coreboot-x210ai), non ancora accettato upstream ([CL 94886](https://review.coreboot.org/c/coreboot/+/94886)).

## Da dove partire

| Documento | Contenuto |
|---|---|
| [docs/GUIDA.md](docs/GUIDA.md) | Procedura di installazione, punto per punto, con i controlli e il ritorno indietro |
| [docs/REPLICARE.md](docs/REPLICARE.md) | Come rifare build, immagine MFIT e verifiche |
| [docs/VERIFICHE.md](docs/VERIFICHE.md) | Cosa è stato misurato sulla scheda, bug noti e decisioni prese |

## Contenuto

| Percorso | Cosa contiene |
|---|---|
| `patches/` | Patch sul fork: tasti luminosità, TPM via PTT |
| `config/` | `coreboot.config` completa, `x210ai.defconfig` minima, `versioni.txt` con i commit esatti |
| `tools/` | Script di lettura, sandbox MFIT, verifica della firma, build, analisi di descriptor, ME, VBT e TPM |

## Cosa non c'è, di proposito

`mfit.exe` e il pacchetto Intel, i dump del chip, le immagini ROM e la `config.xml` del ME. Il software Intel non è ridistribuibile, e i dump contengono dati della singola macchina. `docs/REPLICARE.md` spiega come riottenerli e come verificarli. Il `.gitignore` li esclude.

## Regole che non si violano

1. **Non scrivere mai `coreboot.rom` per intero:** solo la regione BIOS, con `--ifd -i bios`.
2. **Non usare l'immagine Boot Guard di qualcun altro:** solo quella ricavata dal proprio dump.
3. **Non eseguire mai End of Manufacturing** (`MEManuf` o simili) e non toccare `MngHwStatus`.
4. **Non scrivere nulla senza un recupero provato:** chip a 1,8 V, mai programmatori a 3,3 V.
