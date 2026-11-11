# Coreboot su 51NB X210AI

Installazione di coreboot con UEFI (edk2) su X210AI Core Ultra 7 165H: patch, configurazione, strumenti e procedura.

> **Stato al 2026-11-11: nulla è stato scritto sul chip.** L'immagine compila, ma non è mai stata avviata su questa scheda. Prima di scrivere il recupero col T48 deve essere pronto.

Parte dal port di Fionn Cassidy, [WheeledCord/coreboot-x210ai](https://github.com/WheeledCord/coreboot-x210ai), non ancora accettato upstream ([CL 94886](https://review.coreboot.org/c/coreboot/+/94886)).

## Da dove partire

| Documento | Contenuto |
|---|---|
| [docs/STATO.md](docs/STATO.md) | **Dove siamo arrivati e cosa fare dopo: da qui si riprende** |
| [docs/GUIDA.md](docs/GUIDA.md) | Guida completa: Boot Guard, chiavi, manufacturing mode, dump, T48, analisi, MFIT, ME, TPM spento, procedura e problemi |
| [docs/REPLICARE.md](docs/REPLICARE.md) | Come rifare build, immagine MFIT e verifiche |
| [docs/VERIFICHE.md](docs/VERIFICHE.md) | Cosa è stato misurato sulla scheda, bug noti e decisioni prese |
| [docs/VARIANTI.md](docs/VARIANTI.md) | Le tre ROM (edk2, edk2 con TPM, Heads), Windows con Heads e il cambio di firmware |
| [docs/HEADS.md](docs/HEADS.md) | Variante sperimentale con Heads e TPM: mai costruita in Heads né avviata |

## Contenuto

| Percorso | Cosa contiene |
|---|---|
| `patches/` | Patch sul fork: tasti luminosità, Thunderbolt su RP1. In `opzionale/`, non applicate: spegnimento di PTT nel ME e ritorno al TPM |
| `config/` | `coreboot.config` completa, `x210ai.defconfig` minima, `versioni.txt` con i commit esatti |
| `heads/` | Variante Heads sperimentale: scheda, config di coreboot e del kernel, script di build |
| `tools/` | Script di lettura, sandbox MFIT, verifica della firma, build, analisi di descriptor, Boot Guard, ME, VBT e tabella TPM |

## Cosa non c'è, di proposito

`mfit.exe` e il pacchetto Intel, i dump del chip, le immagini ROM e la `config.xml` del ME. Il software Intel non è ridistribuibile, e i dump contengono dati della singola macchina. `docs/REPLICARE.md` spiega come riottenerli e come verificarli. Il `.gitignore` li esclude.

## Regole che non si violano

1. **Non scrivere mai `coreboot.rom` per intero:** solo la regione BIOS, con `--ifd -i bios`.
2. **Non usare l'immagine Boot Guard di qualcun altro:** solo quella ricavata dal proprio dump.
3. **Non eseguire mai End of Manufacturing** (`MEManuf` o simili) e non toccare `MngHwStatus`.
4. **Non scrivere nulla senza un recupero provato:** chip a 1,8 V, mai programmatori a 3,3 V.

## Licenza

Script, patch e documentazione di questa repo sono distribuiti con licenza [GPL-2.0](LICENSE), la stessa di coreboot.

Restano dei rispettivi autori, con le loro condizioni:

- il port di partenza, [WheeledCord/coreboot-x210ai](https://github.com/WheeledCord/coreboot-x210ai), su cui si applicano le patch;
- il software Intel citato (MFIT, FSP, microcode), che qui non è incluso.
