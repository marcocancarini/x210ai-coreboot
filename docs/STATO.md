# Stato del progetto

Aggiornato il 2026-11-07. **Nulla è stato scritto sul chip.** La scheda è ancora col BIOS originale e Boot Guard attivo.

## Fatto

- Manufacturing mode confermato: si può procedere.
- Dump aggiornati, due letture identiche.
- MFIT 18.1.18.2749 ottenuto, firma Intel verificata, immagine `out-bgoff.bin` costruita.
- Coreboot con edk2 compilato, con tasti luminosità, **senza TPM** e con HECI spento (`output-2`).
- T48 compatibile col chip secondo lista e database.
- Scelte: **TPM spento** dal 2026-11-07, per ridurre gli identificativi: [motivi e fonti](GUIDA.md#10-tpm-spento). ME acceso, HECI spento. Niente HAP, niente `me_cleaner`. Heads rimandato.
- Si può flashare dall'interno, purché il recupero col T48 sia pronto.
- Catena di Boot Guard ricalcolata sul dump: hash OEM, KM, BPM e IBB coincidono, firme valide.
- Confermato dal vivo: FPF non scritti (`fpf_soc_lock=0`).
- Guida riscritta, con analisi dei dump e dati personali controllati.
- Confronto con System76: nessun modello Meteor Lake ha moduli ME rimossi, e il ME di questa scheda contiene meno moduli dei loro.

## Dove sono i file

Dump, immagini ROM, log e software Intel restano fuori dalla repo, in una cartella di lavoro locale non versionata. Il firmware dell'EC è nella repo [x210ai-ec](https://github.com/marcocancarini/x210ai-ec).

## Prossimi passi

1. Copiare i backup dei dump su un disco esterno.
2. Aprire la macchina e leggere marking e misura del chip: 8×6 o 6×5 mm.
3. Procurarsi sonda pogo o adattatore WSON-8 della misura giusta e installare Xgpro sul secondo PC. Controllare in Xgpro che le voci `W25Q256JW @WSON8` e `@ISP` indichino 1,8 V.
   Provare la lettura con la sonda sul chip saldato: [sezione 6 della guida](GUIDA.md#6-dump-col-t48-e-pogo-pin).
4. Rifare il dump e ricostruire `out-bgoff.bin`, che deve partire dai dati attuali.
5. Scrivere Boot Guard off, controllare che il BIOS originale parta e che `MSR 0x13A` sia cambiato.
6. Scrivere coreboot e fare le prove del passo 7 della [procedura](GUIDA.md#11-procedura-passo-per-passo).

## Facoltativo, prima del flash

- Rifare la build con il microcode `0x2b` al posto di `0x28`.
- Cercare MFIT 18.0.x e confrontare l'immagine con quella della 18.1.

## Punti aperti

- Il byte `0x448058` di UEP, che MFIT riporta da 1 a 0: funzione ignota. I 518 byte in `0x449000` sono spiegati: [analisi](GUIDA.md#modifiche-di-mfit).
- Comportamento del "Debug Profile" se una verifica fallisce: non documentato.
- Lettura col T48 a chip saldato: non provata.
- MFIT 18.1 non provato su questa scheda.
- Windows mai provato su questo port.
- Tutti i punti aperti sono spiegati nella [sezione 13 della guida](GUIDA.md#13-punti-ancora-da-verificare).
- Versione di Windows da controllare con `winver`: senza TPM gli aggiornamenti di Windows 11 non sono garantiti.
- PTT resta in esecuzione nel ME: la patch `opzionale/0002` lo spegne, ma va provata solo dopo un primo avvio riuscito.
- Tasti luminosità e NVMe: da verificare al primo avvio.
- Thunderbolt: patch non applicata, si riguarda dopo il primo avvio.
- `tools/build.sh` non rieseguito da zero.
