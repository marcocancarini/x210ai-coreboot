# Stato del progetto

Aggiornato il 2026-11-08. **Nulla è stato scritto sul chip.** La scheda è ancora col BIOS originale e Boot Guard attivo.

## Fatto

- Manufacturing mode confermato: si può procedere.
- Dump aggiornati, due letture identiche.
- MFIT 18.1.18.2749 ottenuto, firma Intel verificata, immagine `out-bgoff.bin` costruita.
- Coreboot con edk2 compilato, con tasti luminosità, **senza TPM** e con HECI spento. Dal 2026-11-08 anche microcode `0x2b` e patch Thunderbolt (`output-4`).
- T48 compatibile col chip secondo lista e database.
- Scelte: **TPM spento** dal 2026-11-07, per ridurre gli identificativi: [motivi e fonti](GUIDA.md#10-tpm-spento). ME acceso, HECI spento. Niente HAP, niente `me_cleaner`. Heads scartato: [motivi](VERIFICHE.md#heads).
- Si può flashare dall'interno, purché il recupero col T48 sia pronto.
- Catena di Boot Guard ricalcolata sul dump: hash OEM, KM, BPM e IBB coincidono, firme valide.
- Confermato dal vivo: FPF non scritti (`fpf_soc_lock=0`).
- Guida riscritta, con analisi dei dump e dati personali controllati.
- Confronto con System76: nessun modello Meteor Lake ha moduli ME rimossi, e il ME di questa scheda contiene meno moduli dei loro.
- 2026-11-08: formato di UEP chiarito (due slot, CRC-16 identificato), i 518 byte spiegati, `tools/uep.py`. Boot Guard off ricontrollato offline.
- 2026-11-08: MFIT 18.0.10.2285 trovata, firma Intel valida. Immagine non ancora costruita.
- 2026-11-08: Heads rivalutato e scartato, pro e contro di PTT con HECI spento scritti.

## Dove sono i file

Dump, immagini ROM, log e software Intel restano fuori dalla repo, in una cartella di lavoro locale non versionata. Il firmware dell'EC è nella repo [x210ai-ec](https://github.com/marcocancarini/x210ai-ec).

## Prossimi passi

1. Copiare i backup dei dump su un disco esterno.
2. Aprire la macchina e leggere marking e misura del chip: 8×6 o 6×5 mm.
3. Procurarsi sonda pogo o adattatore WSON-8 della misura giusta e installare Xgpro sul secondo PC. Controllare in Xgpro che le voci `W25Q256JW @WSON8` e `@ISP` indichino 1,8 V.
   Provare la lettura con la sonda sul chip saldato: [sezione 6 della guida](GUIDA.md#6-dump-col-t48-e-pogo-pin).
4. Costruire `out-bgoff.bin` anche con MFIT 18.0 e confrontarla con la 18.1: [comandi](REPLICARE.md#confronto-con-mfit-180).
5. Rifare il dump e ricostruire `out-bgoff.bin`, che deve partire dai dati attuali.
6. Scrivere Boot Guard off, controllare che il BIOS originale parta e che `MSR 0x13A` sia cambiato. Rifare il dump e lanciare `tools/uep.py`.
7. Scrivere coreboot e fare le prove del passo 7 della [procedura](GUIDA.md#11-procedura-passo-per-passo).

## Da fare a mano, in locale

Lavori che Claude non può fare da qui: richiedono la macchina fisica, permessi di root o l'esecuzione di software Intel scaricato.

- [ ] Lanciare MFIT 18.0.10.2285 nel sandbox e confrontare con la 18.1: [comandi](REPLICARE.md#confronto-con-mfit-180). L'esecuzione da Claude è stata bloccata dai permessi il 2026-11-08.
- [ ] Copiare i backup dei dump su un disco esterno.
- [ ] Aprire la macchina, leggere marking e misura del chip.
- [ ] Prova di lettura col T48 sul chip saldato.
- [ ] Rifare il dump con `tools/lettura.sh` (root) prima di scrivere.
- [ ] `winver` su Windows, e i due comandi PowerShell della [sezione 10](GUIDA.md#verifiche).
- [ ] Decidere se committare le modifiche del 2026-11-08 nella repo.

## Punti aperti

- Il byte `0x448058` di UEP, che MFIT riporta da 1 a 0: funzione ignota, ma è l'unica cosa che il ME ha cambiato da solo. I 518 byte in `0x449000` sono spiegati: [analisi](GUIDA.md#i-518-byte-in-0x449000).
- Comportamento del "Debug Profile" se una verifica fallisce: non documentato.
- Lettura col T48 a chip saldato: non provata.
- MFIT 18.1 non provato su questa scheda. La 18.0.10.2285 è pronta ma non ancora eseguita.
- Windows mai provato su questo port.
- Tutti i punti aperti sono spiegati nella [sezione 13 della guida](GUIDA.md#13-punti-ancora-da-verificare).
- Versione di Windows da controllare con `winver`: senza TPM gli aggiornamenti di Windows 11 non sono garantiti.
- PTT resta in esecuzione nel ME: la patch `opzionale/0002` lo spegne, ma va provata solo dopo un primo avvio riuscito.
- Tasti luminosità e NVMe: da verificare al primo avvio.
- Thunderbolt: patch `0004` inclusa ma mai avviata. La retimer ha un GPIO di accensione ignoto, quindi può restare instabile.
- `tools/build.sh` non rieseguito da zero, neanche dopo l'aggiunta del microcode.
- Sicurezza: UEP è protetta solo da un CRC e la flash è scrivibile da root. Vale anche con coreboot: [dettagli](GUIDA.md#i-518-byte-in-0x449000).
