# Stato del progetto

Aggiornato il 2026-11-11. **Nulla è stato scritto sul chip.** La scheda è ancora col BIOS originale e Boot Guard attivo.

## Fatto

- Manufacturing mode confermato: si può procedere.
- Dump aggiornati, due letture identiche.
- MFIT 18.1.18.2749 ottenuto, firma Intel verificata, immagine `out-bgoff.bin` costruita.
- Coreboot con edk2 compilato, con tasti luminosità, **senza TPM** e con HECI spento. Dal 2026-11-08 anche microcode `0x2b` e patch Thunderbolt (`output-4`).
- T48 compatibile col chip secondo lista e database.
- Scelte: **TPM spento** dal 2026-11-07, per ridurre gli identificativi: [motivi e fonti](GUIDA.md#10-tpm-spento). ME acceso, HECI spento. Niente HAP, niente `me_cleaner`. Heads: scartato per la build principale ([motivi](VERIFICHE.md#heads)), aggiunto il 2026-11-11 come variante sperimentale con TPM ([HEADS.md](HEADS.md)).
- Si può flashare dall'interno, purché il recupero col T48 sia pronto.
- Catena di Boot Guard ricalcolata sul dump: hash OEM, KM, BPM e IBB coincidono, firme valide.
- Confermato dal vivo: FPF non scritti (`fpf_soc_lock=0`).
- Guida riscritta, con analisi dei dump e dati personali controllati.
- Confronto con System76: nessun modello Meteor Lake ha moduli ME rimossi, e il ME di questa scheda contiene meno moduli dei loro.
- 2026-11-08: formato di UEP chiarito (due slot, CRC-16 identificato), i 518 byte spiegati, `tools/uep.py`. Boot Guard off ricontrollato offline.
- 2026-11-08: MFIT 18.0.10.2285 trovata, firma Intel valida.
- 2026-11-08: Heads rivalutato e scartato, pro e contro di PTT con HECI spento scritti.
- 2026-11-11: MFIT 18.0 riscaricata con gli stessi hash ed eseguita. Immagine `out-bgoff.bin` costruita e confrontata con la 18.1: UEP, FITC e moduli identici, ma la 18.0 cambia meno byte e non tocca layout del CSE e CDMD. **Raccomandazione: scrivere l'immagine della 18.0** ([risultato](GUIDA.md#risultato-del-confronto-2026-11-11)). Corretto `tools/mfit-sandbox.sh`, che falliva dal secondo avvio.
- 2026-11-11: `tools/build.sh` rieseguito da zero. La ROM è identica bit per bit a `output-4` se costruita nello stesso percorso. Altrove cambia solo il percorso scritto da edk2 nel payload: [dettagli](REPLICARE.md#build-di-coreboot).
- 2026-11-11: variante **Heads sperimentale con TPM** in `heads/`: [docs/HEADS.md](HEADS.md). coreboot della variante compilato fuori da Heads, con microcode identico a `output-4` e 9 MB liberi per l'initrd. Costruita in Heads lo stesso giorno: ROM da 32 MiB, 3,4 MB liberi nella regione BIOS, mai avviata. `patches/opzionale/0003` riallineata, prima non si applicava dopo la `0004`.
- 2026-11-11: `tools/prepara-bgoff.sh` e `verifica-bgoff.py`: build e 16 controlli in un solo comando. Provati sul dump attuale, con la stessa immagine di riferimento, e su 5 casi sbagliati: immagine della 18.1, un bit cambiato nel BIOS o in UEP, MFIT sbagliata, cartella esistente. Tutti fermati.

## Dove sono i file

Dump, immagini ROM, log e software Intel restano fuori dalla repo, in una cartella di lavoro locale non versionata. Il firmware dell'EC è nella repo [x210ai-ec](https://github.com/marcocancarini/x210ai-ec).

## Prossimi passi

1. Copiare i backup dei dump su un disco esterno.
2. Aprire la macchina e leggere marking e misura del chip: 8×6 o 6×5 mm.
3. Procurarsi sonda pogo o adattatore WSON-8 della misura giusta e installare Xgpro sul secondo PC. Controllare in Xgpro che le voci `W25Q256JW @WSON8` e `@ISP` indichino 1,8 V.
   Provare la lettura con la sonda sul chip saldato: [sezione 6 della guida](GUIDA.md#6-dump-col-t48-e-pogo-pin).
4. Rifare il dump con `tools/lettura.sh` e costruire `out-bgoff.bin` con `tools/prepara-bgoff.sh`, che usa MFIT 18.0 e fa tutti i controlli: [passo 3 della procedura](GUIDA.md#3-immagine-con-boot-guard-disattivato).
5. Scrivere Boot Guard off, controllare che il BIOS originale parta e che `MSR 0x13A` sia cambiato. Rifare il dump e lanciare `tools/uep.py`.
6. Scrivere coreboot e fare le prove del passo 7 della [procedura](GUIDA.md#11-procedura-passo-per-passo).

## Da fare a mano, in locale

Lavori che Claude non può fare da qui: richiedono la macchina fisica, permessi di root o l'esecuzione di software Intel scaricato.

- [x] Lanciare MFIT 18.0.10.2285 nel sandbox e confrontare con la 18.1: fatto il 2026-11-11.
- [ ] Copiare i backup dei dump su un disco esterno.
- [ ] Aprire la macchina, leggere marking e misura del chip.
- [ ] Prova di lettura col T48 sul chip saldato.
- [ ] Rifare il dump con `tools/lettura.sh` (root) prima di scrivere.
- [x] Installare Docker e lanciare `heads/build-heads.sh`: fatto il 2026-11-11.
- [ ] `winver` su Windows, e i due comandi PowerShell della [sezione 10](GUIDA.md#verifiche).
- [x] Decidere se committare le modifiche del 2026-11-08 nella repo: committate in `f3285e5`.

## Punti aperti

- Il byte `0x448058` di UEP, che MFIT riporta da 1 a 0: funzione ignota, ma è l'unica cosa che il ME ha cambiato da solo. I 518 byte in `0x449000` sono spiegati: [analisi](GUIDA.md#i-518-byte-in-0x449000).
- Comportamento del "Debug Profile" se una verifica fallisce: non documentato.
- Lettura col T48 a chip saldato: non provata.
- MFIT: le due versioni sono equivalenti nelle parti funzionali. Usando la 18.0 si ripete la combinazione già avviata dall'autore, mentre la 18.1 resta non provata su questa scheda.
- Windows mai provato su questo port.
- Tutti i punti aperti sono spiegati nella [sezione 13 della guida](GUIDA.md#13-punti-ancora-da-verificare).
- Versione di Windows da controllare con `winver`: senza TPM gli aggiornamenti di Windows 11 non sono garantiti.
- PTT resta in esecuzione nel ME: la patch `opzionale/0002` lo spegne, ma va provata solo dopo un primo avvio riuscito.
- Tasti luminosità e NVMe: da verificare al primo avvio.
- Thunderbolt: patch `0004` inclusa ma mai avviata. La retimer ha un GPIO di accensione ignoto, quindi può restare instabile.
- Heads: `/boot` su btrfs e PTT con HECI spento non provati: [elenco](HEADS.md#cosa-non-è-verificato).
- Sicurezza: UEP è protetta solo da un CRC e la flash è scrivibile da root. Vale anche con coreboot: [dettagli](GUIDA.md#i-518-byte-in-0x449000).
