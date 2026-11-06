# Stato del progetto

Aggiornato il 2026-11-06. **Nulla è stato scritto sul chip.** La scheda è ancora col BIOS originale e Boot Guard attivo.

## Fatto

- Manufacturing mode confermato: si può procedere.
- Dump aggiornati, due letture identiche.
- MFIT 18.1.18.2749 ottenuto, firma Intel verificata, immagine `out-bgoff.bin` costruita.
- Coreboot con edk2 compilato, con tasti luminosità, TPM via PTT e HECI spento.
- T48 compatibile col chip secondo lista e database.
- Scelte: tenere il TPM, ME acceso col minimo di funzioni, HECI spento. Niente HAP, niente `me_cleaner`. Heads rimandato.
- Si può flashare dall'interno, purché il recupero col T48 sia pronto.

## Dove sono i file

Dump, immagini ROM, log e software Intel restano fuori dalla repo, in una cartella di lavoro locale non versionata. Il firmware dell'EC è nella repo [x210ai-ec](https://github.com/marcocancarini/x210ai-ec).

## Prossimi passi

1. Copiare i backup dei dump su un disco esterno.
2. Aprire la macchina e leggere marking e misura del chip: 8×6 o 6×5 mm.
3. Procurarsi l'adattatore WSON-8 giusto e installare Xgpro sul secondo PC. Controllare in Xgpro che `W25Q256JW @WSON8` indichi 1,8 V.
4. Rifare il dump e ricostruire `out-bgoff.bin`, che deve partire dai dati attuali.
5. Scrivere Boot Guard off, controllare che il BIOS originale parta e che `MSR 0x13A` sia cambiato.
6. Scrivere coreboot e fare le prove del passo 7 di [GUIDA.md](GUIDA.md).

## Facoltativo, prima del flash

- Rifare la build con il microcode `0x2b` al posto di `0x28`.
- Cercare MFIT 18.0.x e confrontare l'immagine con quella della 18.1.

## Punti aperti

- 518 byte in UEP cambiati da MFIT e non spiegati.
- MFIT 18.1 non provato su questa scheda.
- Windows mai provato su questo port.
- PTT con HECI spento, tasti luminosità e NVMe: da verificare al primo avvio.
- Thunderbolt: patch non applicata, si riguarda dopo il primo avvio.
- `tools/build.sh` non rieseguito da zero.
