# Guida a coreboot su 51NB X210AI

Questa guida parte da quella di Fionn Cassidy, autore del port ([`x210ai.md`](https://github.com/WheeledCord/coreboot-x210ai/blob/x210ai/Documentation/mainboard/51nb/x210ai.md)), e la adatta a questa scheda: Core Ultra 7 165H, ME 18.0.5.2098, pannello 2560x1600, Wi-Fi AX210, Windows e CachyOS sullo stesso disco.

> **Stato al 2026-11-07: nulla è stato scritto sul chip.** Boot Guard è ancora attivo. La ROM da usare è quella **senza TPM** in `output-2`. Le analisi sono state fatte sui dump, le scritture dei passi 4 e 6 non sono mai state provate qui.

Nel testo, **misurato** indica un dato letto da questa scheda o dai suoi dump, **dedotto** un'interpretazione nostra, **non provato** qualcosa che nessuno ha ancora verificato qui.

## Indice

**Capire**

1. [Cosa cambia rispetto alla guida originale](#1-cosa-cambia-rispetto-alla-guida-originale)
2. [Boot Guard](#2-boot-guard)
3. [Chiavi: enrollment e dove stanno](#3-chiavi-enrollment-e-dove-stanno)
4. [Manufacturing mode](#4-manufacturing-mode)
5. [Dump con flashrom](#5-dump-con-flashrom)
6. [Dump col T48 e pogo pin](#6-dump-col-t48-e-pogo-pin)
7. [Analisi dei dump](#7-analisi-dei-dump)
8. [Il passaggio in MFIT](#8-il-passaggio-in-mfit)
9. [Ridurre Intel ME](#9-ridurre-intel-me)
10. [TPM spento](#10-tpm-spento)

**Fare**

11. [Procedura passo per passo](#11-procedura-passo-per-passo)
12. [Problemi possibili](#12-problemi-possibili)
13. [Punti ancora da verificare](#13-punti-ancora-da-verificare)
14. [Fonti](#14-fonti)

---

## 1. Cosa cambia rispetto alla guida originale

La sequenza è la stessa: controllare il manufacturing mode, disattivare Boot Guard sul proprio dump, scrivere coreboot nella sola regione BIOS. Cambiano questi punti:

| Guida originale | Qui | Perché |
|---|---|---|
| `flashrom -p internal -r dump.bin` | Prima si scollega il driver SPI, poi due letture da confrontare | Col driver caricato flashrom vede solo un "Opaque flash chip", senza regioni né protezioni |
| `mfit --loadconfig config.xml --build ...` | Nella stessa riga anche `--decompose dump.bin` | È il comando usato qui: la config rimanda ai file estratti dal dump |
| `flashrom -p internal -w dump_bgdisabled.bin`, chip intero | Solo la regione ME, oppure T48 a macchina spenta | MFIT cambia solo il ME; riscrivere tutto a sistema acceso riporta indietro anche le variabili UEFI |
| "SPI programmer" generico | T48 a 1,8 V, mai 3,3 V | Il chip è un W25Q256JW |
| MFIT 18.0.10.2285 | MFIT 18.1.18.2749 | È l'unica versione ottenuta. Non è provata su questa scheda |
| TPM non provato, "PTT non abilitato" | PTT è attivo col BIOS originale, ma qui viene **tolto di proposito** | Misurato: `PttSupported=Yes`. Motivi nella [sezione 10](#10-tpm-spento) |
| Provato solo su Linux | Windows da provare per primo | Windows serve su questa macchina |
| Niente tasti luminosità | `_Q06` e `_Q07` aggiunti | Ricavati dal DSDT originale |

Stato del port al 2026-11-07: fork fermo a `f0877e0d3c` del 2026-09-01, [CL 94886](https://review.coreboot.org/c/coreboot/+/94886) ancora `NEW`, patch set 4, 8 commenti non risolti.

---

## 2. Boot Guard

Boot Guard fa controllare al processore il firmware **prima** che venga eseguita la sua prima istruzione. Finché è attivo con queste chiavi, coreboot non può partire: non è firmato e non contiene le strutture richieste.

### La catena

```text
Hash della chiave OEM  ──── fusibili FPF, oppure qui immagine del ME
        │ controlla
        ▼
Key Manifest (KM)      ──── firmato con la chiave OEM, contiene l'hash della chiave BPM
        │ autorizza
        ▼
Boot Policy (BPM)      ──── firmato con la chiave BPM, contiene l'hash dell'IBB
        │ controlla
        ▼
Initial Boot Block     ──── primo codice del BIOS, poi prosegue con la propria verifica
```

### All'accensione

1. Il ME parte per primo, dalla sua ROM, e carica il proprio firmware dalla regione ME.
2. Il microcodice legge il puntatore alla **FIT** (Firmware Interface Table), 64 byte prima della fine del chip.
3. Dalla FIT carica l'aggiornamento del microcodice e la **Authenticated Code Module** (ACM), un modulo firmato da Intel che il processore verifica da solo.
4. La ACM riceve la configurazione di Boot Guard e controlla in ordine KM, BPM e IBB.
5. Se tutto torna, il processore salta al vettore di reset. Altrimenti applica la politica configurata.

La ACM riporta l'esito nel registro **MSR `0x13A`**. Decodifica del valore misurato `0x30000006f`, secondo `src/security/intel/cbnt/logging.c`:

| Bit | Campo | Valore | Significato |
|---|---|---|---|
| 0 | NEM | 1 | La ACM ha preparato la cache come RAM |
| 1-2 | Tipo TPM | 3 | PTT |
| 3 | TPM success | 1 | TPM usabile |
| 4 | FACB | 0 | Dedotto: avvio tramite ACM non imposto dai fusibili |
| 5 | Measured boot | 1 | Attivo |
| 6 | Verified boot | **1** | **Attivo: è questo il bit da far sparire** |
| 7 | Revoked | 0 | Nessuna revoca |
| 32 | Boot Guard capable | 1 | Processore capace di Boot Guard |
| 34 | TXT capable | 0 | Coerente con `TxtSupported=No` |

Il bit 33 è senza nome nel codice di coreboot.

### Il profilo "Debug Profile"

In MFIT il campo `BtGuardProfileConfig` ammette quattro valori: `Boot Guard Disabled`, `Debug Profile`, `Verified Boot`, `Verified and Measured Boot`. Questa scheda è in `Debug Profile`.

Intel non documenta pubblicamente questo profilo. Il registro mostra verified e measured boot entrambi attivi, ma non dice cosa succede se una verifica fallisce. Per questo la guida si attiene alla regola prudente del port: finché Boot Guard non è disattivato, coreboot non si scrive.

---

## 3. Chiavi: enrollment e dove stanno

### Come funziona l'enrollment

L'enrollment di Boot Guard non è una procedura per l'utente. Lo fa il produttore:

1. Genera una chiave OEM e una chiave per la BPM, e tiene per sé le parti private.
2. Firma BPM e KM, e li mette nel BIOS.
3. In MFIT inserisce l'hash della chiave OEM e sceglie il profilo.
4. Scrive l'immagine sulla scheda. Il valore resta nella configurazione del ME.
5. Con l'**End of Manufacturing** (EOM) la configurazione finisce nei fusibili FPF.

Secondo [Intel](https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/resources/key-usage-in-integrated-firmware-images.html), durante lo sviluppo le politiche possono stare nelle variabili non volatili del ME e vengono scritte nei fusibili all'EOM. Da lì in poi non cambiano più per tutta la vita della scheda.

**Il passo 5 su questa scheda non è mai stato fatto.** La chiave è stata registrata, ma solo in flash. Ecco perché basta riscrivere la flash.

In teoria si potrebbe registrare una chiave propria e firmare coreboot, ottenendo un Boot Guard sotto il proprio controllo. Questa guida non lo prevede: il port non genera KM né BPM, e un errore in quella procedura può lasciare la scheda senza avvio.

Non vanno confuse con le chiavi di **Secure Boot** (PK, KEK, db): stanno nelle variabili UEFI e controllano il sistema operativo, non il firmware. Con coreboot ed edk2 si riparte da variabili nuove.

### Dove sono su questa scheda

Valori misurati. Gli offset sono relativi all'inizio del chip.

| Elemento | Dove | Dettagli |
|---|---|---|
| Chiave di verifica della ACM | Processore | Fissa, Intel |
| ACM | BIOS, `0x1F40000` | Firmata Intel, datata 2023-07-20, build di produzione (bit debug a 0) |
| Chiave OEM privata | Non è sulla macchina | Nelle strutture analizzate ci sono solo chiavi pubbliche e hash |
| Hash chiave OEM (SHA-384) | ME: 3 volte in OEMP a `0x1C6524`, `0x1C655C`, `0x1C6594`, e in UEP a `0x4480A0`, `0x4490A0` | Inizia con `306e2e04…` |
| Fusibili FPF | Nel SoC, non nel chip SPI | **Non scritti:** `fpf_soc_lock=0` |
| Key Manifest attivo | BIOS, `0x1EE3B00` | Contiene la chiave OEM pubblica, RSA-3072. ID 1, come `BtGuardKeyManifestId` |
| BPM attiva | BIOS, `0x1EE3080` | Contiene la chiave BPM pubblica, RSA-3072 |
| Politica attiva | ME, in UEP | MFIT modifica il byte `0x448053` |
| IBB | BIOS, `0x1B90000` (1,6 MiB) e `0x1FC0000` (256 KiB) | Digest SHA-1, SHA-256, SHA-384 e SM3 nella BPM |

In `0x1D30000` ci sono altre copie di KM e BPM: la FIT non le usa, e l'IBB descritto dalla prima BPM non coincide con il contenuto del chip. Non hanno effetto.

---

## 4. Manufacturing mode

Il termine corretto è **manufacturing mode**, non "maintenance mode": è la fase in cui la scheda è ancora "in fabbrica" e la configurazione del ME non è stata fissata. È ciò che rende possibile l'intero progetto. Se il produttore avesse eseguito l'EOM, Boot Guard resterebbe attivo per sempre e coreboot non si potrebbe installare.

Non va confuso con la Security Override del ME o con la modalità di debug: sono altre cose e qui non servono.

### Come si controlla

```sh
cat /sys/class/mei/mei0/fw_status      # non serve root
sudo setpci -s 00:16.0 0x40.l          # la riga della guida originale
```

Valori misurati. La decodifica viene da `me_18.h` e `cse_spec.c` di coreboot.

| Registro | Valore | Lettura |
|---|---|---|
| HFSTS1 | `90000255` | Stato 5 (normale), **`mfg_mode=1`**, inizializzazione completata, errore 0, modo operativo 0 |
| HFSTS3 | `00000020` | SKU 2: Consumer, quindi niente AMT |
| HFSTS6 | `00000000` | **`fpf_soc_lock=0`** (FPF non scritti), `manuf_lock=0` (variabili non bloccate) |

Per coreboot, su ME 18 la scheda esce dal manufacturing mode solo quando `mfg_mode` è a 0 e i due lock sono a 1. Qui sono tutti nello stato opposto.

### La regola

**Mai eseguire l'EOM.** È irreversibile e renderebbe definitivi l'hash della chiave e il profilo presenti in quel momento.

Attenzione in particolare a:

- `Fpt.efi -closemnf`: **`Fpt.efi` è nel pacchetto del produttore.** Il suo `fb.nsh` esegue solo `fpt.efi -f`, ma quello strumento può chiudere il manufacturing mode.
- `MEManuf` e strumenti simili del pacchetto CSME.
- Le opzioni di MFIT legate a EOM e FPF, come `MngHwStatus` e `PttSupportedFpf`. `EomFirstBootEnabled` è a `No` e deve restare così.

**EOP non è EOM.** Nella configurazione di coreboot compare `SOC_INTEL_CSE_SEND_EOP_LATE=y`. EOP significa End of POST: è un messaggio inviato al ME a ogni avvio per dirgli che il firmware ha finito. Non scrive fusibili e non chiude il manufacturing mode.

Il rovescio della medaglia è la sicurezza: con la flash aperta e Boot Guard spento, chi ottiene root può riscrivere il firmware, e nessun controllo all'avvio lo rileverebbe.

---

## 5. Dump con flashrom

**Sì, i dump via flashrom sono possibili**, e sono stati fatti: due letture con lo stesso hash. Funziona perché su questa scheda nessuna delle protezioni che potrebbero bloccarlo è attiva.

| Protezione | Cosa fa | Qui |
|---|---|---|
| Permessi nel descriptor | Dicono quali regioni ogni "master" può leggere e scrivere | `FLMSTR1=ffffffff`: la CPU può tutto |
| Protected Range | Blocca intervalli del chip nel controller SPI | Nessuno segnalato |
| Protezione SMM del BIOS | Limita la scrittura al firmware in SMM | Nessun avviso di flashrom |
| Status register del chip | Protezione dentro il chip | `--wp-status`: `disabled` |
| `FLOCKDN` | Congela la configurazione del controller | **Attivo**, ma non vieta nulla qui |

I messaggi che sembrano errori sono normali:

- **`SPI Configuration is locked down`:** è `FLOCKDN`. La configurazione non si può più cambiare, ma quella congelata lascia tutto aperto.
- **`Enabling hardware sequencing because some important opcode is locked`:** flashrom usa il sequenziamento hardware del controller invece di comporre i comandi a mano.

### Il driver del kernel

Con `spi_intel_pci` caricato, Linux tiene il controller ed espone `/dev/mtd0`. Flashrom passa da lì e mostra `Opaque flash chip`: la lettura riesce, ma regioni e protezioni restano invisibili. Scollegando il driver, flashrom parla direttamente col controller.

```sh
sudo bash tools/lettura.sh
```

Lo script scollega il driver, legge due volte, controlla le protezioni e lo ricollega. Non scrive sul chip.

### Limiti

- **Una lettura a sistema acceso non è una fotografia.** Il ME e il BIOS possono scrivere durante la lettura, quindi servono sempre due letture identiche. Se differiscono, si rilegge.
- **Un dump invecchia.** Tra il 4 e il 6 novembre sono cambiati 16 blocchi da 4 KiB nel MFS del ME e 7 nelle variabili UEFI. Descriptor, resto del ME, DevExp2 e resto del BIOS sono identici.
- **Leggere non garantisce di poter scrivere.** I permessi dicono di sì, ma la prova arriva solo con la prima scrittura vera. Va quindi preparato il recupero.
- **Flashrom non aiuta se la macchina non parte.** Per quello esiste il T48.

---

## 6. Dump col T48 e pogo pin

**Il T48 è compatibile col chip. I pogo pin sono possibili, ma su questa scheda non sono provati.** Il dubbio riguarda la lettura col chip ancora saldato, non il T48.

### Il chip

| Voce | Valore | Stato |
|---|---|---|
| Modello | Winbond W25Q256JW, ID `ef6019`, 32 MiB | Misurato |
| Tensione | 1,8 V, intervallo 1,7-1,95 V | Modello misurato, tensione da scheda tecnica |
| Voce T48 | `W25Q256JW @WSON8`, lista V13.16 | Database minipro: stessa voce di `@SOIC8`, `chip_id=0x00ef6019`, `voltages=0x0206` = 1,8 V |
| Voce ISP | `W25Q256JW @ISP` | Solo nella lista ufficiale, non nel database minipro: controllare in Xgpro |
| Package | WSON-8 secondo il port | **Da misurare** |

Il W25Q256JW esiste in entrambe le misure: **8×6 mm** (`W25Q256JWE…`) e **6×5 mm** (`W25Q256JWP…`). Sonda e adattatore devono corrispondere, quindi prima si apre la macchina e si leggono marking e misura col calibro. La posizione è nella foto della [guida originale](https://github.com/WheeledCord/coreboot-x210ai/blob/x210ai/Documentation/mainboard/51nb/x210ai.md#flashing).

Piedini, uguali a SOIC-8: 1 `/CS`, 2 `DO`, 3 `/WP`, 4 `GND`, 5 `DI`, 6 `CLK`, 7 `/HOLD`, 8 `VCC`.

### Le tre vie

| Via | Vantaggi | Problemi | Giudizio |
|---|---|---|---|
| **Pogo pin sul chip saldato** | Non si dissalda nulla, reversibile | Contatto fragile, alimenta anche la scheda | **Da provare per prima, in sola lettura** |
| Clip SOIC | Comoda | Su un WSON non si aggancia | Non usare |
| **Chip dissaldato su adattatore WSON-8** | Il metodo più pulito | Serve aria calda e mano ferma | Da usare se la sonda fallisce |

### Perché il pogo pin non è garantito

- **Il T48 alimenta anche la scheda.** Il VCC del chip è collegato al resto della linea a 1,8 V, e non sappiamo cosa alimenti. La corrente può non bastare e dare letture sporche. Il manuale del TL866II, modello precedente, indica 120 mA: per il T48 non abbiamo trovato un dato.
- **I segnali non sono solo del chip.** `CLK`, `/CS`, `DI` e `DO` arrivano anche al chipset, che da spento può caricarli.
- **Su un WSON i contatti sono sotto il package.** La sonda tocca solo il bordo delle piazzole o la saldatura, e va tenuta ferma per tutta la lettura, che dura minuti.
- **`/WP` può impedire di scrivere.** Se sulla scheda è a massa la lettura funziona, ma la scrittura no.
- **Non abbiamo trovato prove pubbliche** di questa combinazione: T48, W25Q256JW e pogo pin su una scheda portatile.

### Come collegarlo

Il VCC del T48 arriva a 1,8 V e il suo connettore ICSP gestisce memorie SPI serie 25. Si usa la voce `@ISP` con lo schema dei collegamenti mostrato da Xgpro: non abbiamo trovato una piedinatura pubblica affidabile, quindi non va presa da altri modelli.

1. Scollegare alimentatore e batteria. Lasciare la scheda scarica per qualche minuto.
2. Controllare col multimetro che tra VCC e massa non ci sia un corto.
3. In Xgpro scegliere la voce, controllare che indichi **1,8 V** e leggere solo l'ID.
4. Tenere ferma la sonda con un supporto, allineando il piedino 1.
5. Se l'ID è `ef6019`, leggere tutto il chip due volte.
6. Controllare il risultato (punto successivo).

Se l'ID è sbagliato o cambia, non insistere e **non scrivere**: si passa alla dissaldatura. Non scegliere mai la voce `W25Q256JV`, che è a 3 V.

### Cosa deve risultare

Le due letture devono avere lo stesso hash, e il contenuto deve coincidere col dump di flashrom salvo blocchi del MFS e delle variabili UEFI:

```sh
python3 -I tools/confronta-regioni.py backup/fresh1.bin lettura-t48.bin
```

Un'area iniziale piena di `FF`, o differenze nei moduli del ME, indicano una lettura cattiva.

### Quando il recupero è davvero pronto

Solo una **scrittura verificata** dimostra che il T48 può salvare la scheda: si riscrive il dump appena letto e si rilegge. Con i pogo pin ha un rischio proprio, perché un contatto perso a metà lascia il chip incompleto. Va fatta con la dissaldatura a portata di mano.

---

## 7. Analisi dei dump

Tutti i dati vengono dai dump del 2026-11-04 e del 2026-11-06, e si rifanno con:

```sh
python3 -I tools/analisi-bootguard.py backup/fresh1.bin
python3 -I tools/descriptor.py backup/fresh1.bin
```

### Mappa del chip

Identica a `board.fmd` del port.

| Regione | Da | A | Dimensione | Note |
|---|---|---|---|---|
| Descriptor | `0x0000000` | `0x0003FFF` | 16 KiB | Firma `0x0FF0A55A` a `0x10` |
| ME | `0x0004000` | `0x0814FFF` | 8260 KiB | 3376 KiB usati, il resto è `FF` |
| Device Expansion 2 | `0x0815000` | `0x11FFFFF` | 10156 KiB | **Interamente `FF`** |
| BIOS | `0x1200000` | `0x1FFFFFF` | 14 MiB | Coreboot sostituisce solo questa |

Le regioni GbE ed EC non esistono. Il firmware dell'EC sta dentro l'IT5571 e nessun passo di questa guida lo tocca.

### Catena di Boot Guard

Abbiamo ricalcolato ogni anello sui byte del dump, partendo dalla FIT:

| Controllo | Esito |
|---|---|
| SHA-384 di modulo ed esponente della chiave del KM = `OemPublicKeyHash` di MFIT | **Coincide** |
| Firma del KM, RSA-3072 PSS con SHA-384 | **Valida** |
| SHA-256 della chiave BPM = hash contenuto nel KM | **Coincide** |
| Firma della BPM, RSA-3072 PSS con SHA-256 | **Valida** |
| Digest dell'IBB, SHA-1, SHA-256 e SHA-384 | **Coincidono** |

Quindi l'immagine è integra e firmata correttamente, e `OemPublicKeyHash` è davvero l'ancora della catena. SM3 non è stato ricalcolato.

Il controllo segue lo stesso percorso della ACM, un anello alla volta:

1. **Si parte dalla FIT.** Il puntatore è negli ultimi 64 byte del chip e porta a KM e BPM attivi. Partire da qui conta: la prima analisi aveva preso una copia inutilizzata in `0x1D30000`, e i digest non tornavano.
2. **KM.** Si estraggono modulo ed esponente della chiave, se ne calcola lo SHA-384 e lo si confronta col valore in MFIT. Poi si verifica la firma RSA del KM con quella stessa chiave.
3. **BPM.** La sua chiave pubblica deve avere lo SHA-256 scritto nel KM, e con quella chiave si verifica la firma della BPM.
4. **IBB.** La BPM elenca due segmenti. Si concatenano i byte del chip in quegli intervalli e si confrontano gli hash con quelli scritti nella BPM.

Che cosa dimostra: i byte letti da flashrom sono coerenti, il dump non è corrotto nelle parti critiche, e Boot Guard si appoggia a quella chiave. Che cosa **non** dimostra: come si comporta la scheda dopo la modifica. Quello si vede solo avviandola.

La ROM di coreboot, al confronto, ha nella FIT solo tre voci di microcodice: niente ACM, KM o BPM. Descriptor e ME sono `FF`, ed è il motivo per cui **non va mai scritta per intero**.

### Modifiche di MFIT

Confronto tra dump, ricostruzione di controllo con `config.xml` invariata e immagine con Boot Guard disattivato:

| Zona | Dump → controllo | Controllo → Boot Guard off |
|---|---|---|
| Descriptor, DevExp2, BIOS | Identici | Identici |
| MFS | Identico | Identico |
| Moduli del firmware | Identici | Identici |
| Metadati `0x4000`, `0x5000`, `0x2A5000`, `0x3A6000`, `0x44A000` | 45 byte | Nulla |
| FITC | 19 byte | Nulla |
| CDMD | 4088 byte | Nulla |
| UEP, copia principale | 3 byte | **3 byte** |
| UEP, seconda copia | 518 byte azzerati a `FF` | Nulla |

La colonna di destra è l'effetto del cambio di profilo. Quella di sinistra è ciò che MFIT riscrive comunque, anche senza alcuna modifica: per questo serve la ricostruzione di controllo, che separa le due cose.

#### I 3 byte che disattivano Boot Guard

| Offset | Controllo | Boot Guard off | Significato |
|---|---|---|---|
| `0x448004`-`0x448005` | `83 A8` | `79 A7` | Checksum di UEP (dedotto: cambia insieme al contenuto) |
| `0x448053` | `D8` | `18` | Profilo di Boot Guard |

Da `0xD8` a `0x18` si azzerano i due bit più alti. L'unica opzione cambiata in `config.xml` è il profilo, quindi l'associazione è certa. Il significato del singolo bit invece è dedotto, perché Intel non pubblica il formato di UEP.

KM, BPM e hash della chiave restano nel chip. Senza una politica attiva non dovrebbero più essere applicati (dedotto): lo conferma il port, dove il BIOS originale continua a partire. Per questo tornare indietro è facile, e anche per questo il controllo del passo 4 guarda il bit 6 dell'MSR e non la presenza del KM.

#### I 518 byte in `0x449000`

Il dump contiene due copie di UEP. Confrontandole si vede che cosa è successo:

| Campo | Copia principale `0x448000` | Seconda copia `0x449000` | Ricostruita da MFIT |
|---|---|---|---|
| Firma, 4 byte | `$UEP` | `00 00 00 00` | `$UEP` / `FF` |
| Checksum, 2 byte | `A6 38` | `83 A8` | `83 A8` / `FF` |
| Byte `+0x58` | `01` | `00` | `00` / `FF` |
| Resto | Uguale | Uguale | Uguale / `FF` |

Sono esattamente 7 byte di differenza tra le due copie. La lettura più semplice (dedotta) è questa: la seconda copia è la versione di fabbrica, invalidata azzerandone la firma, e la principale è quella riscritta dal ME quando ha alzato il byte `+0x58`. Il checksum della seconda copia coincide con quello ricostruito da MFIT, il che la conferma.

MFIT riparte dalla configurazione, quindi produce UEP come appena uscita dalla fabbrica: byte `+0x58` a 0 e seconda copia vuota (i 518 byte diventano `FF`).

**Conseguenza pratica:** il ME vedrà quel flag azzerato, e non sappiamo a cosa serva. Potrebbe solo segnare "primo avvio completato". Dovrebbe capitare a chiunque ricostruisca l'immagine con MFIT, come ha fatto l'autore del port. Il rischio sembra basso, ma il primo avvio va osservato ([sezione 13](#13-punti-ancora-da-verificare)).

### Dati personali

**Non pubblicare mai un dump.** Il controllo è stato fatto cercando i valori della macchina, senza riportarli qui:

| Dato | Esito | Dove |
|---|---|---|
| MAC Ethernet e Wi-Fi | Non trovati | — |
| Product key Windows, tabelle MSDM o SLIC | Non trovati | — |
| Nome utente, hostname, email | Non trovati | — |
| Numero di serie, SKU, asset tag | Valori generici del produttore, assenti dal dump | — |
| **UUID di sistema** | **Presente 22 volte in forma binaria** | Dump |
| **Voci di avvio** | Presenti, con riferimenti a dischi e partizioni | Variabili UEFI |
| **`OfflineUniqueIDEKPub`** | Presente: dal nome, chiave pubblica di endorsement del TPM | Variabili UEFI |
| **`AMITSESetup`** | Presente: impostazioni e password del BIOS | Variabili UEFI |
| **`HwErrRec0000`** | Presenti: registri di errori hardware | Variabili UEFI |
| **MFS** | 500 KiB opachi, specifici della macchina e non decodificati | ME |

Le voci in grassetto restano nel dump e non vanno condivise. In questa guida valgono due regole: niente hash completi dei dump, perché li identificano, e niente UUID, partizioni o percorsi personali. L'hash della chiave OEM è abbreviato: identifica il produttore, non la singola macchina (dedotto).

Perché contano:

- **UUID:** non contiene dati su di te, ma identifica questa macchina in modo stabile. Pubblicarlo collega il dump a ogni servizio che lo legge.
- **Voci di avvio:** i percorsi includono gli identificativi delle partizioni, quindi descrivono i tuoi dischi.
- **Chiave di endorsement:** è pubblica per natura, ma è unica per ogni TPM. Funziona come un numero di serie.
- **`AMITSESetup`:** non è stato decodificato. Se è impostata una password del BIOS, va considerata esposta.
- **Registri di errore:** possono contenere date e dettagli dell'hardware.
- **MFS:** contiene lo stato del ME, compreso con ogni probabilità quello di PTT (dedotto). Non è leggibile, ma scrivere il MFS di un'altra scheda sarebbe un errore, e pubblicare il proprio non ha alcun vantaggio.

**Limite del controllo:** si sono cercati i valori noti, in testo, UTF-16 e binario dove sensato. Il MFS non è stato decodificato, e un valore codificato in altro modo sfuggirebbe. Per questo la regola resta non pubblicare il dump, anche se la ricerca non trova nulla.

---

## 8. Il passaggio in MFIT

MFIT, *Modular Flash Image Tool*, è il programma Intel con cui i produttori compongono l'immagine. Scompone un dump, ne mostra la configurazione e lo ricostruisce. **Non scrive sul chip:** produce solo un file.

### Ottenerlo e verificarlo

Serve una versione per Meteor Lake-P. Provenienza, hash e controllo della firma Intel sono in [REPLICARE.md](REPLICARE.md#ottenere-mfit). Qui lo si esegue con wine, senza rete e con accesso alla sola cartella di lavoro, tramite `tools/mfit-sandbox.sh`.

### Riga di comando (via usata)

```sh
mkdir lavoro && cp fresh1.bin lavoro/

# 1. Scompone il dump ed estrae la configurazione
tools/mfit-sandbox.sh mfit.exe lavoro --decompose fresh1.bin --saveconfig config.xml

# 2. Cambia un solo valore
cp lavoro/config.xml lavoro/config-bg.xml
sed -i 's/<BtGuardProfileConfig value="Debug Profile"/<BtGuardProfileConfig value="Boot Guard Disabled"/' lavoro/config-bg.xml

# 3. Ricostruisce l'immagine
tools/mfit-sandbox.sh mfit.exe lavoro --decompose fresh1.bin --loadconfig config-bg.xml --build out-bgoff.bin
```

Il percorso in `OemExtInputFile` punta ai file estratti dal dump, quindi la cartella di lavoro deve restare la stessa.

### Interfaccia grafica

Non provata qui: i nomi vengono dalla struttura di `config.xml`.

1. Aprire `mfit.exe` su Windows e caricare il dump con il layout *MeteorLake P and ArrowLake P Chipsets - Consumer - SPI*.
2. Andare in **Platform Protection → Boot Guard Configuration**.
3. Cambiare **Boot Guard Profile** da `Debug Profile` a `Boot Guard Disabled`.
4. Non toccare altro, in particolare **OEM Public Key Hash** e **Key Manifest ID**.
5. Costruire l'immagine.

### Cosa aspettarsi nel log

`fit.log` deve terminare con `'out-bgoff.bin' image built successfully`, senza righe `ERROR`. Qui ci sono 56 `WARNING`: 55 sono del tipo `Cannot write NVAR ... is read-only`, cioè impostazioni che MFIT conserva ma non può cambiare su un dump scomposto.

### Controlli sull'immagine

```sh
python3 -I tools/confronta-regioni.py lavoro/fresh1.bin lavoro/out-bgoff.bin
python3 -I tools/analisi-bootguard.py lavoro/out-bgoff.bin
```

**Controllo:** descriptor, DevExp2 e BIOS identici, catena ancora valida, e riscomponendo l'immagine `BtGuardProfileConfig value="Boot Guard Disabled"`.

MFIT 18.1 ricostruisce un firmware costruito con la 18.0.5. Tutte le verifiche passano, ma nessuno ha avviato questa combinazione.

---

## 9. Ridurre Intel ME

**Si può ridurre ciò che il ME espone, non si possono togliere pezzi in sicurezza.** Il firmware di questa scheda è già piccolo, e dentro la regione ME non c'è solo il ME.

Questa sezione è stata scritta quando il TPM doveva restare. Ora non è più un vincolo: il rifiuto di HAP e `me_state` per via del TPM va riletto con la [sezione 10](#10-tpm-spento). Restano validi gli altri motivi.

### Cosa c'è dentro

Valori misurati, nomi dalle strutture del firmware. Le funzioni sono dedotte dai nomi.

| Partizione | Spazio | Usati | Funzione | Toglibile? |
|---|---|---|---|---|
| RBEP | 1464 KiB | 1176 KiB | Nucleo del ME: `kernel`, `bup`, `crypto`, `fpf`, `heci`, `fwupdate`, `espi`, **`ptt`** | **No** |
| PMCP | 328 KiB | 256 KiB | Controller dell'alimentazione | No |
| PCOD | 448 KiB | 292 KiB | Punit, gestione energia del processore | No |
| DCOD | 384 KiB | 208 KiB | Display | No |
| SPHY, NPHY | 452 KiB | 220 KiB | PHY | No |
| PCHC | 40 KiB | 24 KiB | Configurazione del chipset | No |
| IOMP, TBTP | 396 KiB | 360 KiB | USB-C e Thunderbolt | No, se servono |
| EFWP | 192 KiB | 152 KiB | Non identificata | No |
| ADSP, IUNP | 168 KiB | 76 KiB | Audio DSP, fotocamera | Non provato |
| OEMP | 4 KiB | 4 KiB | OEM Key Manifest | No |
| Dati (`$FPT`) | 656 KiB | 476 KiB | MFS, log, FITC, UEP | No |
| NFTP | 3712 KiB | **132 KiB** | `fdo`, `sigma`, `hotham`, `icc`, `mctp`, `ish_srv`, altri | Quasi vuota |

Nessun modulo ha nomi legati ad AMT: l'immagine è Consumer. Nella configurazione sono già spenti ISH (`IshSupported=No`) e FIDO (`FidoSupported=Disabled`), mentre TXT è `No`.

### Le opzioni

| Opzione | Effetto | Scelta |
|---|---|---|
| **Togliere moduli** con `me_cleaner` | Su ME 12 e successivi la rimozione non è supportata, e PMC, Punit e PHY non sono opzionali. In coreboot `USE_ME_CLEANER` arriva solo fino a Kaby Lake | **No** |
| **Bit HAP** | Ferma il ME dopo l'avvio. L'offset su Meteor Lake non è confermato | **No**, finché non è confermato |
| **Disattivazione via HECI** (`me_state`, come System76) | Spegne anche PTT (dedotto), che ora va bene. Reversibile ([confronto sotto](#confronto-con-system76)) | **Possibile:** livello 3 della [sezione 10](#10-tpm-spento) |
| **HECI spento prima del payload** | `DISABLE_HECI1_AT_PRE_BOOT`: il sistema operativo non vede `/dev/mei0` | **Sì, nella build** |
| **Impostazioni MFIT** | 55 sono in sola lettura, quindi `PttSupported`, `IshSupported` e `FidoSupported` non si cambiano da un dump | Nessuna |
| **`MngHwStatus`, `PttSupportedFpf`** | Disattivazioni permanenti tramite FPF | **Mai** |

### Il bit HAP su Meteor Lake

**Non usare `ifdtool -M` su questa scheda.** HAP è un bit nelle soft strap del descriptor: se è a 1, il ME si ferma dopo l'inizializzazione di base. `ifdtool` lo cerca sempre nello stesso posto per tutti i descriptor moderni: bit 16 di `PCHSTRP0`.

Su Meteor Lake quel posto è sbagliato, e lo si vede da tre prove:

| Prova | Risultato |
|---|---|
| `PCHSTRP0` del nostro dump | `0xFB034D80`: il bit 16 è a 1 |
| `ifdtool -p mtl -d` | `HAP bit is set` |
| Stato reale del ME | Attivo: HFSTS1 in stato 5, `/dev/mei0` presente, PTT funzionante |

`ifdtool` quindi dice che il ME è fermo mentre è in funzione. `-M 0` e `-M 1` cambierebbero una strap di cui non conosciamo il significato, con effetti imprevedibili all'avvio. Anche i `README` di System76 scrivono `HAP: true` per i modelli Meteor Lake, dove lo stesso bit è a 1 nei loro descriptor: non va preso come prova che il ME sia spento.

Il fork [me_cleaner_thinkpad](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad) elenca l'offset di ME 18 come sconosciuto, con `0x21E` come candidato sperimentale non confermato. Nel nostro dump quel byte vale `0x10`, col bit 0 a zero, che è compatibile con un ME attivo, e vale lo stesso nei descriptor Meteor Lake di System76. Dasharo offre "Disabled (HAP)" sui suoi portatili, e un utente lo riporta attivo su un NovaCustom V540TU Meteor Lake, quindi il meccanismo esiste. Per noi resta no finché l'offset non è confermato.

### Confronto con System76

System76 pubblica i firmware dei suoi portatili in [firmware-open](https://github.com/system76/firmware-open), quindi si può controllare che cosa fa davvero. Abbiamo esaminato i 50 modelli con `me.rom` e confrontato i binari.

**Risposta breve: nessun System76 Meteor Lake ha componenti del ME rimossi.** I soli modelli con `me_cleaner` sono tre Galago Pro con ME 11.8, molto più vecchi.

| Modelli | ME | Come riducono il ME | TPM |
|---|---|---|---|
| **galp2, galp3, galp3-b** | 11.8.70, piattaforma `kbl-u` | **Moduli rimossi:** `USE_ME_CLEANER=y`, default `-S`, applicato alla compilazione | Componente `pc80/tpm`, non PTT |
| **darp10, lemp13** (Meteor Lake) | 18.0.5 | Nessun modulo rimosso. `me_state=Disable`: spento via HECI a ogni avvio | Componente `pc80/tpm`, non PTT |
| **meer9** (Meteor Lake) | 18.0.5 | Nessun modulo rimosso, **ME acceso** (`me_state=Enable`) | **PTT** (`HAVE_INTEL_PTT`, `CRB_TPM`) |

Nessun altro `coreboot.config` dei 50 modelli attiva `USE_ME_CLEANER`. Delle piattaforme controllate, quasi tutte hanno `me_state=Disable`: le eccezioni sono `kbl-u`, che usa `me_cleaner`, `meer9`, e `tgl-u`, che ha `Enable` perché non ha S3 e richiede S0ix. La [documentazione di System76](https://github.com/system76/firmware-open/blob/master/docs/intel-me.md) lo dice apertamente: `me_cleaner` "non supporta la versione del ME usata su molti dei nostri sistemi", quindi si manda un comando HECI nelle prime fasi di avvio.

#### Perché `me_cleaner` funzionava lì e qui no

Il ME 11.8 di galp3 ha una tabella `$FPT` semplice, con le partizioni `FTPR` e `NFTP`, e il suo strumento sa cancellare la seconda. Il ME 18 sta in un formato diverso, a blocchi BPDT, con partizioni di PMC, Punit, PHY e Thunderbolt nello stesso contenitore. Le parti da togliere non sono più una zona unica e separabile.

#### Il tuo ME contro darp10

darp10 è il confronto più diretto: stessa versione 18.0.5.2098 e stesso formato.

| | X210AI | darp10 |
|---|---|---|
| Totale dei moduli | **3546 KiB** | 7497 KiB |
| NFTP | 8 moduli, 192 KiB | 15 moduli, 3224 KiB |
| Moduli in più | Nessuno | `amt` (2576 KiB), `wlan_drv` (292 KiB), `gde`, `usbr`, `psr`, `wapps`, `vdm`, `upid_ca`, `upid_app` |
| Partizioni in più | IUNP | ISHC, LOCL, WCOD |
| AMT | Modulo assente | Modulo presente, ME spento via HECI |

Ogni modulo del tuo ME esiste anche in darp10, non il contrario: **il tuo firmware contiene meno codice di quello di un System76 Meteor Lake**. Lo ha ridotto Intel scegliendo l'immagine Consumer, senza interventi di terzi, e conserva le firme originali.

Il confronto serve anche da verifica: `PMCP`, `TBTP`, `PCHC`, `NPHY`, `IOMP`, `EFWP` e `DCOD` sono **identici byte per byte** a quelli di darp10, compresi i 21 moduli di PMCP. Conferma che sono firmware Intel comuni, non cose specifiche del ME o di 51NB. I moduli di `RBEP` e `NFTP` hanno gli stessi nomi ma byte diversi, compreso `ptt`, che ha la stessa dimensione: sono build diverse dello stesso firmware (dedotto).

#### Che cosa insegna

- **ME e PTT vanno insieme.** System76 spegne il ME sui portatili con TPM separato, e sul meer9, che usa PTT, lo tiene acceso. Non è una prova che PTT smetta di funzionare col ME spento, ma va in quella direzione.
- **La X210AI usa PTT.** L'MSR `0x13A` riporta PTT come tipo di TPM, e un componente separato non risulta. Spegnere il ME dovrebbe quindi spegnere anche il TPM (dedotto), che ora è ciò che si vuole.
- **Lo spegnimento via HECI è reversibile.** È un'opzione CMOS, che a ogni cambio fa un reset globale. Non tocca la flash, a differenza di HAP o `me_cleaner`.
- **Ha un costo sulla sospensione.** Secondo System76, con il ME spento la CPU si ferma allo stato C8, e in s2idle il consumo passa da circa 1 a circa 3 W. In S3 il problema non si pone, e il port usa S3.
- **`me_state` su questa scheda richiederebbe modifiche al port.** Il codice c'è in `cse.c`, ma la board non ha tabella opzioni né `cmos.layout`. Con `OPTION_BACKEND_NONE` il ME resta acceso. Va aggiunto anche `me_state_counter`, che evita riavvii ciclici se il ME non cambia stato dopo 3 tentativi.

**Attenzione:** quei file vanno solo studiati. I `me.rom` di System76 sono per le loro schede, senza i tuoi dati nel MFS e con chiavi diverse: **non vanno mai scritti su questa scheda**.

---

## 10. TPM spento

**Decisione del 2026-11-07: niente TPM.** Sostituisce la scelta precedente di tenere PTT. Il motivo è che il TPM offre un identificativo unico e permanente della macchina, usabile da Windows.

### Cosa dicono le fonti

Questi punti sono scritti nero su bianco da chi definisce lo standard e da chi fa Windows.

| Fatto | Fonte | Testo originale |
|---|---|---|
| L'EK può identificare utente o piattaforma | [TCG, EK Credential Profile 2.6, §2.3](https://cdn.trustedcomputinggroup.org/production/TCG_EK_Credential_Profile_for_TPM_Family_2_0_Level_0_Version_2_6_pub_c2d4e91986.pdf) | "Because an Endorsement Key is unique to a TPM and usually has a long lifetime, it could be used to identify a user or a platform." |
| L'uso diretto dell'EK può aggregare attività | [TCG, TPM 2.0 Library Part 1, §9.4.4.4](https://cdn.trustedcomputinggroup.org/production/TCG_TPM_2_r1p64_Part1_Architecture_15may2021_2f86d24103.pdf) | "...could result in aggregation of activity logs. Analysis of the aggregated activity could reveal personal information..." |
| Il certificato dell'EK identifica il TPM | [Microsoft, How Windows uses the TPM](https://learn.microsoft.com/en-us/windows/security/hardware-security/tpm/how-windows-uses-the-tpm) | "...endorsement key certificate that can uniquely identify the TPM" |
| Windows dà alle app un ID di sistema basato per primo sul TPM | [Microsoft, GetSystemIdForPublisher](https://learn.microsoft.com/en-us/uwp/api/windows.system.profile.systemidentification.getsystemidforpublisher) | "The method will first attempt to use the Trusted Platform Module (TPM), if present, to get an ID." |
| Quell'ID sopravvive alle reinstallazioni | Stessa pagina | "Persists across restarts, reinstalls and upgrades of Windows, including clean installs" |
| Windows ha il modo di ottenere l'EK | [Microsoft, Get-TpmEndorsementKeyInfo](https://learn.microsoft.com/en-us/powershell/module/trustedplatformmodule/get-tpmendorsementkeyinfo?view=windowsserver2025-ps) | Comando PowerShell di Windows che legge l'EK pubblico e i suoi certificati |
| Con Autopilot, Windows chiede a Intel il certificato dell'EK | [Microsoft, Autopilot requirements](https://learn.microsoft.com/en-us/autopilot/requirements?tabs=networking) | "Intel: `https://ekop.intel.com/ekcertservice`" |

**Misurato su questa macchina:** la variabile UEFI `OfflineUniqueIDEKPub` è leggibile da qualsiasi utente in Linux e ha 256 byte di dati, con primo bit alto e ultimo bit dispari, proprio come un modulo RSA-2048. Sta in due copie nel dump. Coincide con la descrizione data da [terze parti](https://www.sysnative.com/forums/threads/what-is-the-offlineuniqueidekpub-context.41840/) (la parte pubblica dell'EK). Microsoft non documenta questa variabile, e non l'abbiamo confrontata con l'EK reale.

### Cosa le fonti non dicono

Queste precisazioni servono a non sopravvalutare il problema.

- **Non abbiamo trovato prove che Windows mandi l'EK a Microsoft per tracciare i PC di casa.** L'identificabilità è documentata, un invio sistematico no.
- **Microsoft dichiara di fare il contrario, negli scenari di attestazione.** "To protect privacy, most TPM scenarios don't directly use an actual endorsement key", e usa chiavi separate "to prevent separate evaluators from collaborating to track the same device". È una sua dichiarazione, non verificata da noi.
- **L'ID di `GetSystemIdForPublisher` non è l'EK.** È specifico per editore e app: "apps by different publishers on the same system will obtain different IDs". Però tutte le app non pacchettizzate ricevono lo stesso valore: "identical for all unpackaged (Win32) apps".
- **Il TCG pone un limite:** "Unless the EK is certified by a trusted entity [...] the public portion of the EK is not privacy sensitive". L'EK di PTT però è certificabile da Intel, quindi il limite qui serve a poco.
- **Il testo TCG Part 1 citato è la revisione 1.64 in public review.** Il profilo EK 2.6 è pubblicato.

In sintesi: "il TPM è un identificativo unico che Windows può usare" è vero e documentato. "Windows lo usa per tracciarti" non è dimostrato. Spegnerlo è una scelta ragionevole di riduzione del rischio, non la rimozione di un tracciamento accertato.

### Cosa cambia davvero

Spegnere il TPM **non** rende anonima la macchina. Microsoft stessa dice che dopo il TPM si passa ad altro: "If a TPM is not present, the method will try to get an ID from the Unified Extensible Firmware Interface (UEFI)". Per Autopilot i campi d'identità sono "SMBIOS UUID", "MAC address" e "Unique disk serial number".

| Identificativo | Col BIOS originale | Con questa build | Note |
|---|---|---|---|
| EK del TPM | Esposto | **Non più esposto** | Resta nel chip, ma il sistema non lo trova |
| `OfflineUniqueIDEKPub` | Presente | **Assente** | Le variabili di coreboot ripartono vuote. Torna se si ripristina il dump |
| ID di sistema Windows | Da TPM | **Da UEFI** | Dedotto: la differenza è che ora sta in una zona che si può cancellare |
| UUID SMBIOS | Presente | **Tutto zero** | Misurato nel codice: `smbios_system_set_uuid` non lo imposta |
| Seriale SMBIOS | Generico | `123456789` | Uguale per chiunque usi il port |
| MAC Ethernet e Wi-Fi | Presente | **Invariato** | Identifica la macchina anche senza TPM |
| Seriale del disco | Presente | **Invariato** | Come sopra |
| Account Microsoft | Se usato | **Invariato** | Identifica te, non solo la macchina |
| Dati già salvati in Windows | Presenti | **Invariati** | Una reinstallazione pulita non è stata provata come rimedio |

Il guadagno vero è questo: **un identificativo fissato nell'hardware diventa uno cancellabile.** L'ID da UEFI, secondo [un'analisi di terze parti](https://mastodon.social/@slipstream/99514497819803181), vive in `OfflineUniqueIDRandomSeed`: si azzera svuotando le variabili. Sulla tua macchina oggi quella variabile non esiste, perché c'è il TPM.

### Come si spegne

Ci sono tre livelli. Ognuno include il precedente, e conviene salirli uno alla volta.

| Livello | Cosa fa | Effetto sul TPM | Stato |
|---|---|---|---|
| **1. Niente TPM nel firmware** | Toglie il supporto da coreboot e da edk2 (`CONFIG_NO_TPM`, `EDK2_DISABLE_TPM`) | Il sistema non lo vede. PTT continua a girare nel ME | **Compilato**, mai avviato |
| **2. PTT spento nel ME** | `cse_enable_ptt(false)`, patch `patches/opzionale/0002-x210ai-spegni-ptt.patch` | PTT disattivato nel ME | Patch compilata, mai eseguita |
| **3. ME spento via HECI** | `me_state=Disable`, come i portatili System76 | Spegne il ME dopo l'avvio, PTT compreso (dedotto) | Richiede modifiche al port |

Controllo sulla ROM del livello 1: nessuna stringa `MSFT0101`, `TPM2` o `Tcg2`, nessun dispositivo TPM nel DSDT, `CONFIG_NO_TPM=y`, e `_Q06` e `_Q07` ancora presenti. Il controllo vale per ciò che è scritto nella ROM: le tabelle generate all'avvio si vedono solo sulla macchina.

**Il livello 1 nasconde, non spegne.** Windows cerca il TPM nelle tabelle ACPI (dedotto), quindi non lo trova, ma il firmware PTT è ancora in esecuzione. Per l'obiettivo pratico dovrebbe bastare.

**Il livello 2 è quello che lo spegne davvero**, ma va provato solo **dopo** che coreboot parte bene:

- Il comando arriva al ME e poi forza un reset globale. Se su ME 18 il comando venisse accettato senza effetto, il reset si ripeterebbe a ogni avvio. Sarebbe un **ciclo di riavvii**, recuperabile solo col T48.
- Il precedente è `protectli/vault_cml`, un Comet Lake. Su Meteor Lake non risulta provato.
- Si annulla con una build che chiama `cse_enable_ptt(true)`.

**Il livello 3** ha un buon precedente: darp10 usa lo stesso ME 18.0.5.2098 con `me_state=Disable`. Ora che il TPM non è più un vincolo è praticabile, e riprende l'obiettivo "ME minimo". Vedi il [confronto con System76](#confronto-con-system76).

Da non confondere: **`TPM2_Clear` non cambia l'EK.** `TPM2_ChangeEPS` invece lo cambia, ma [richiede l'autorizzazione della piattaforma](https://trustedcomputinggroup.org/wp-content/uploads/TCG-TPM-v2.0-Provisioning-Guidance-Published-v1r1.pdf), quindi dal sistema operativo in genere non si può.

### Conseguenze su Windows

| Voce | Effetto | Fonte |
|---|---|---|
| **Windows 11, requisiti** | "To install or upgrade to Windows 11", TPM 2.0 è un requisito | [Microsoft](https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements) |
| **Aggiornamenti** | "aren't guaranteed to receive updates, including but not limited to security updates" | [Microsoft](https://support.microsoft.com/en-us/windows/installing-windows-11-on-devices-that-don-t-meet-minimum-system-requirements-0b2dc4a2-5933-4ad4-9c09-ef0a331518f1) |
| **Supporto** | "your device won't receive support from Microsoft", e compare una filigrana sul desktop | Stessa pagina |
| **Aggiornamenti di versione** | Potrebbero rifiutarsi di installarsi (dedotto dal requisito) | Non provato |
| **Windows Hello** | Le chiavi passano a protezione software: "software-based techniques protect the key" | [Microsoft](https://learn.microsoft.com/en-us/windows/security/hardware-security/tpm/how-windows-uses-the-tpm) |
| **PIN esistente** | Va ricreato | Non provato |
| **Crittografia del dispositivo** | Non disponibile nella forma automatica "TPM-only" | Stessa pagina Microsoft |
| **BitLocker** | Assente qui, quindi nessuna perdita di dati | Misurato: `TYPE="ntfs"` |
| **Linux** | Nessuna perdita, salvo dischi sbloccati dal TPM | Da controllare |

**Il rischio più serio è perdere gli aggiornamenti di sicurezza di Windows 11.** La versione installata va controllata prima: su una macchina esposta a Internet pesa più del beneficio sul tracciamento, a meno che Windows non sia usato poco o isolato.

### Verifiche

Prima, su Windows, per conoscere il punto di partenza (non provato). Il risultato atteso è `Tpm`:

```powershell
[Windows.System.Profile.SystemIdentification,Windows.System.Profile,ContentType=WindowsRuntime]::GetSystemIdForPublisher().Source
Get-Tpm | Select-Object TpmPresent
```

Dopo il primo avvio con coreboot:

| Controllo | Atteso |
|---|---|
| Linux: `ls /dev/tpm*` | Nessun dispositivo |
| Linux: `ls /sys/firmware/efi/efivars \| grep OfflineUnique` | Nessuna voce `OfflineUniqueIDEKPub` |
| Linux: `sudo dmidecode -s system-uuid` | Tutti zeri |
| Windows: i due comandi sopra | `Uefi` e `TpmPresent : False` |

---

## 11. Procedura passo per passo

Ogni passo ha un controllo: se fallisce, ci si ferma.

### 0. Prerequisiti

- [ ] XGecu T48 con Xgpro aggiornato su un secondo PC Windows.
- [ ] Marking e misura del chip letti.
- [ ] Sonda pogo WSON-8 della misura giusta, oppure adattatore e attrezzatura per dissaldare.
- [ ] `backup/` copiata su un disco esterno leggibile dal secondo PC.
- [ ] Chiavetta con una distribuzione live.
- [ ] Alimentatore collegato durante ogni scrittura interna.
- [ ] Licenza Windows collegata all'account Microsoft: cambiando firmware può chiedere una nuova attivazione.
- [ ] Niente dischi sbloccati dal TPM, oppure chiavi di recupero a portata di mano.
- [ ] Versione di Windows controllata e conseguenze accettate ([sezione 10](#10-tpm-spento)).
- [ ] Niente EOM, in nessuno strumento.

### 1. Letture dalla scheda

```sh
sudo bash tools/lettura.sh
```

**Controllo:** `mfg_mode=1` e `fpf_soc_lock=0` ([sezione 4](#4-manufacturing-mode)), HFSTS1 `90000255`, due letture con lo stesso hash. Altrimenti coreboot non è installabile.

### 2. Recupero col T48

Seguire la [sezione 6](#6-dump-col-t48-e-pogo-pin). Dall'interno si può flashare senza programmatore, ma il T48 è l'unico modo di recuperare la scheda se non si riavvia. Deve essere pronto **prima** della prima scrittura.

**Controllo:** due letture col T48 uguali tra loro e coerenti col dump, e prova di scrittura superata. Saltando la prova di scrittura, il recupero resta non dimostrato.

### 3. Immagine con Boot Guard disattivato

Ripetere il dump poco prima, così l'immagine contiene i dati attuali, e costruire l'immagine come nella [sezione 8](#8-il-passaggio-in-mfit).

**Controllo:** quelli della sezione 8.

### 4. Scrittura di Boot Guard off

**Con il T48 (più prudente):** macchina spenta, immagine intera `out-bgoff.bin`. Il ME è fermo e non può interferire.

**Dall'interno:** solo la regione ME, subito dopo il dump, a sistema fermo e con l'alimentatore collegato. Il ME è in esecuzione, quindi la scrittura può entrare in conflitto con ciò che sta facendo (non provato).

```sh
sudo modprobe -r spi_intel_pci spi_intel
sudo flashrom -p internal --ifd -i me -N -w out-bgoff.bin
```

Poi spegnere del tutto, staccare l'alimentatore per almeno 30 secondi e riaccendere: un riavvio semplice potrebbe non ricaricare il ME.

**Controllo:** il BIOS originale parte, Linux e Windows partono, e in MSR `0x13A` il bit 6 è a 0. Prima era `0x30000006f`. `fpf_soc_lock` deve restare 0.

**Se non parte:** col T48, riscrivere il dump originale.

### 5. Preparazione

- Salvare un nuovo dump: è il riferimento per tornare indietro con Boot Guard già disattivato.
- Annotare le voci di avvio con `efibootmgr`.

### 6. Scrittura di coreboot

**Solo la regione BIOS:** la ROM ha descriptor e ME vuoti. Usare `output-2/coreboot.rom`, che è la build senza TPM.

```sh
sudo modprobe -r spi_intel_pci spi_intel
sudo flashrom -p internal --ifd -i bios -N -w coreboot.rom
```

Il primo avvio può durare minuti per l'addestramento della RAM: non interrompere.

### 7. Primo avvio

Nelle variabili UEFI nuove non ci sono voci di avvio. Se entrambe le ESP hanno `BOOTX64.EFI`, può partire Windows invece di CachyOS. Da CachyOS, indicando disco e partizioni corretti:

```sh
sudo efibootmgr -c -d /dev/nvmeXn1 -p <ESP-Linux> -L CachyOS -l '\EFI\BOOT\BOOTX64.EFI'
sudo efibootmgr -c -d /dev/nvmeXn1 -p <ESP-Windows> -L Windows -l '\EFI\Microsoft\Boot\bootmgfw.efi'
```

Da verificare, in quest'ordine:

| Prova | Comando o azione |
|---|---|
| Windows si avvia | È il primo test: il port è provato solo con Linux |
| NVMe | Un revisore segnala una root port non trovata. Qui il disco è a `00:06.0` |
| TPM assente | Le verifiche della [sezione 10](#verifiche) |
| HECI spento | `/dev/mei0` assente |
| Tastiera e touchpad, incluse le combinazioni Fn | Prova manuale |
| Luminosità | Tasti Fn, su Linux e Windows |
| Batteria, coperchio, sospensione S3 | Prova manuale |
| Wi-Fi AX210, Ethernet, audio, HDMI/DP | Prova manuale |
| Video | `vainfo`, perché `mei_gsc_proxy` può servire alla decodifica |
| USB-C e Thunderbolt | Instabili anche col BIOS originale |

### 8. Tornare indietro

- **Il sistema parte ancora:** riscrivere la sola regione BIOS del dump del passo 5.

  ```sh
  sudo modprobe -r spi_intel_pci spi_intel
  sudo flashrom -p internal --ifd -i bios -N -w dump-passo-5.bin
  ```

- **Non parte:** T48 con il dump completo.

Il firmware EC non è toccato da nessuno di questi passi.

---

## 12. Problemi possibili

### Prima di scrivere

| Sintomo | Causa probabile | Cosa fare |
|---|---|---|
| `Opaque flash chip` | Driver SPI del kernel caricato | `sudo modprobe -r spi_intel_pci spi_intel` |
| Modulo in uso | Altro processo su `/dev/mtd0` | Chiuderlo e riprovare |
| Due letture diverse | ME o BIOS hanno scritto nel frattempo | Rileggere. Se succede sempre, confrontare i blocchi |
| `mfg_mode=0` o `fpf_soc_lock=1` | Scheda chiusa | **Fermarsi:** Boot Guard non si può disattivare così |
| MFIT non riconosce il dump | Versione non adatta a Meteor Lake-P | Usare la versione giusta, verificando la firma |
| `OemExtInputFile` non trovato | Cartella di lavoro cambiata | Rifare `--decompose` nella stessa cartella |

### Col T48

| Sintomo | Causa probabile | Cosa fare |
|---|---|---|
| ID errato, `000000`, `FFFFFF` | Contatto, orientamento o scheda che assorbe | Ricontrollare piedino 1 e misura. Dopo pochi tentativi passare alla dissaldatura |
| Lettura con blocchi `FF` | Contatto instabile | Scartare il file, fissare la sonda |
| Hash diversi tra letture | Contatto o bus disturbato | Non scrivere |
| Lettura sì, scrittura no | `/WP` a massa o protezione attiva | Sonda inadatta a scrivere: dissaldare |
| Chip che non risponde dopo una prova a 3,3 V | Chip probabilmente danneggiato | Sostituirlo con uno uguale e riscrivere il dump |

### Scrittura interna

| Sintomo | Causa probabile | Cosa fare |
|---|---|---|
| Errore di transazione o regione negata | Una protezione non vista | **Non riavviare.** Rileggere e confrontare il chip. Se è intatto, si può passare al T48 |
| Scrittura interrotta | Corrente, crash | **Non spegnere.** Riprovare subito finché il sistema è vivo |
| Verifica fallita nella regione ME | Il ME ha scritto durante l'operazione | Rileggere e confrontare. Se incerto, usare il T48 da spento |

### Al primo riavvio

| Sintomo | Causa probabile | Cosa fare |
|---|---|---|
| Boot Guard off: macchina che non parte | Immagine non accettata, per esempio con MFIT 18.1 | T48 col dump originale. Provare poi una MFIT 18.0.x |
| Bit 6 dell'MSR ancora a 1 | ME non ricaricato | Spegnimento completo senza alimentatore |
| BIOS originale con ME in errore | Regione ME incoerente | Leggere `fw_status`, riscrivere il ME originale |
| Coreboot: schermo nero | Addestramento della RAM | Aspettare parecchi minuti prima di concludere |
| Coreboot: schermo nero persistente | Boot Guard ancora attivo o ROM sbagliata | T48 col dump del passo 5 |
| Parte Windows invece di CachyOS | Nessuna voce di avvio | Passo 7 |
| Nessun disco | Root port PCIe non attivata | Controllare `devicetree.cb`, tornare al BIOS originale |
| Immagine di un altro utente che non parte | Dati legati alla singola macchina (dedotto) | **Usare solo il proprio dump.** Il fork ha ritirato la sua immagine dopo due fallimenti |

### Dopo il primo avvio

| Sintomo | Causa probabile | Cosa fare |
|---|---|---|
| Windows chiede l'attivazione | Firmware cambiato | Riattivare dall'account Microsoft |
| PIN di Windows Hello non funziona | Misure del TPM cambiate | Ricreare il PIN |
| Disco non si sblocca da solo | Chiave legata ai PCR | Chiave di recupero, poi registrare di nuovo |
| TPM ancora visibile | Build sbagliata, per esempio `coreboot.rom` di `output-1` | Controllare che sia la ROM senza TPM |
| Windows rifiuta un aggiornamento | Requisito TPM 2.0 | [Sezione 10](#conseguenze-su-windows). Se è inaccettabile, usare la build con TPM di `output-1` |
| `vainfo` limitato | `mei_gsc_proxy` senza HECI | Rifare la build con HECI acceso, se serve il video |
| Tasti luminosità fermi | Patch `_Q06`, `_Q07` non provata | Controllare gli eventi ACPI |
| Sospensione rotta | `INTEL_TME` attivo | Controllare che sia disattivato |
| Thunderbolt o USB-C instabili | Problema noto del port | Vedere [VERIFICHE.md](VERIFICHE.md#bug-noti) |
| Secure Boot senza chiavi | Variabili UEFI nuove | Registrare di nuovo le chiavi |

---

## 13. Punti ancora da verificare

Per ognuno: perché conta, come si scopre la risposta e cosa fare se va male.

### MFIT 18.1 su questa scheda

**Il dubbio:** l'autore ha usato MFIT 18.0.10.2285, noi 18.1.18.2749, su un firmware costruito con la 18.0.5.

**Perché conta:** una versione più nuova potrebbe scrivere strutture che il ME 18.0.5 interpreta in modo diverso. Le verifiche offline dicono che moduli e configurazione restano uguali, ma l'unico giudizio vero è del ME all'avvio.

**Come si verifica:** passo 4, guardando che il sistema parta e che HFSTS1 resti con errore 0.

**Se va male:** T48 col dump originale. Poi cercare una MFIT 18.0.x, confrontando le due immagini prima di scrivere.

### Il byte `0x448058` di UEP

**Il dubbio:** MFIT lo riporta da 1 a 0 e non sappiamo a cosa serva ([analisi](#i-518-byte-in-0x449000)).

**Perché conta:** è l'unica differenza funzionale, oltre al profilo, rispetto a ciò che il ME ha scritto da solo.

**Come si verifica:** dopo il passo 4, rifare il dump. Se il byte torna a 1 e compare di nuovo una seconda copia in `0x449000`, il ME ha ripetuto lo stesso aggiornamento, ed è un buon segno. Confrontare anche `fw_status`.

**Se va male:** se compaiono errori del ME, T48 col dump originale.

### Comportamento del "Debug Profile"

**Il dubbio:** Intel non documenta cosa succede a una verifica fallita in questo profilo. Il registro dice solo che verified e measured boot sono attivi.

**Perché conta:** poco, per l'installazione: si disattiva comunque. Conta per capire se un errore di firma blocca la macchina o lascia un avviso.

**Come si verifica:** servirebbe far fallire apposta una verifica, cioè scrivere qualcosa di non firmato. **Non vale il rischio:** si lascia aperto.

### Lettura col T48 a chip saldato

**Il dubbio:** il T48 riesce a leggere con la scheda collegata alla linea a 1,8 V?

**Perché conta:** decide se il recupero si può fare senza dissaldare ([sezione 6](#6-dump-col-t48-e-pogo-pin)).

**Come si verifica:** lettura dell'ID, due letture complete e confronto col dump.

**Se va male:** dissaldatura su adattatore WSON-8, da organizzare **prima** di scrivere.

### Misura del chip

**Il dubbio:** 8×6 o 6×5 mm. Il modello esiste in entrambe le misure.

**Perché conta:** sonda e adattatore sono specifici per misura.

**Come si verifica:** aprire la macchina, leggere il marking, usare il calibro. È il primo passo pratico.

### La prima scrittura

**Il dubbio:** flashrom può davvero scrivere la regione ME e quella BIOS a sistema acceso?

**Perché conta:** permessi e registri dicono di sì, ma la prova arriva solo con una scrittura vera. Una protezione invisibile lascerebbe un errore a metà.

**Come si verifica:** passo 4. In alternativa si evita il dubbio usando il T48 a macchina spenta.

**Se va male:** [problemi nella scrittura interna](#scrittura-interna). Non riavviare prima di aver confrontato il contenuto del chip.

### Stato del sistema dopo Boot Guard off

**Il dubbio:** quale valore avrà l'MSR `0x13A`? Sappiamo solo che il bit 6 deve andare a 0. Il port non riporta il valore completo.

**Perché conta:** è la prova che la modifica ha avuto effetto.

**Come si verifica:** `tools/lettura.sh`, e annotare il valore in [VERIFICHE.md](VERIFICHE.md).

### Windows con coreboot

**Il dubbio:** il port è provato solo con Linux, e Windows serve su questa macchina.

**Perché conta:** tabelle ACPI, S3, TPM e driver ME possono comportarsi diversamente.

**Come si verifica:** è la prima prova del passo 7. I driver Intel ME di Windows potrebbero lamentarsi dell'HECI spento.

**Se va male:** BIOS originale con il dump del passo 5. Linux resta avviabile, quindi non è un blocco del sistema.

### Livello 2: PTT spento nel ME

**Il dubbio:** `cse_enable_ptt(false)` funziona su ME 18?

**Perché conta:** è l'unico modo di spegnere PTT lasciando acceso il ME. Il livello 1 lo nasconde soltanto.

**Come si verifica:** solo dopo un avvio riuscito del livello 1, con il T48 pronto. Nel log di coreboot deve comparire una sola volta il comando, seguita da un solo reset.

**Se va male:** un ciclo di riavvii si recupera col T48, riscrivendo una ROM senza la patch.

### Windows senza TPM

**Il dubbio:** quale versione di Windows è installata, e continua ad aggiornarsi senza TPM?

**Perché conta:** gli aggiornamenti di sicurezza non sono garantiti su Windows 11.

**Come si verifica:** `winver` adesso. Dopo, Windows Update per qualche settimana.

**Se va male:** si torna alla ROM con TPM.

### Altri punti del port

| Punto | Come si verifica |
|---|---|
| Tasti luminosità | Tasti Fn su Linux e Windows |
| Root port NVMe | Il disco a `00:06.0` compare |
| Decodifica video senza HECI | `vainfo` |
| Thunderbolt | Prova dopo il primo avvio, con la patch della review solo se serve |
| Microcode `0x28` nella ROM, `0x2b` nel sistema | `dmesg \| grep microcode` |
| `tools/build.sh` da zero | Eseguirlo su una cartella pulita |

---

## 14. Fonti

**Port e progetto**

- [Guida originale di Fionn Cassidy](https://github.com/WheeledCord/coreboot-x210ai/blob/x210ai/Documentation/mainboard/51nb/x210ai.md)
- [CL 94886](https://review.coreboot.org/c/coreboot/+/94886)
- In coreboot: `me_18.h`, `cse_spec.c`, `src/security/intel/cbnt/logging.c`, `util/ifdtool/ifdtool.c`

**Boot Guard e ME**

- [Intel: Key Usage in Integrated Firmware Images](https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/resources/key-usage-in-integrated-firmware-images.html)
- [3mdeb: dimostrazione di Boot Guard](https://blog.3mdeb.com/2020/2020-02-18-ew2020-btg-demo/)
- [me_cleaner_thinkpad](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad): fork non verificato, usato solo per lo stato di HAP
- [Dasharo: Intel ME](https://docs.dasharo.com/osf-trivia-list/me/)
- [NovaCustom: disattivare il ME](https://novacustom.com/knowledge-base/how-to-disable-the-intel-management-engine/)
- [Report Qubes su V540TU](https://forum.qubes-os.org/t/novacustom-v54-series-v540tu-dasharo-coreboot-uefi/33116)

**TPM e identificazione**

- [TCG EK Credential Profile 2.6](https://cdn.trustedcomputinggroup.org/production/TCG_EK_Credential_Profile_for_TPM_Family_2_0_Level_0_Version_2_6_pub_c2d4e91986.pdf)
- [TCG TPM 2.0 Library Part 1, rev. 1.64, public review](https://cdn.trustedcomputinggroup.org/production/TCG_TPM_2_r1p64_Part1_Architecture_15may2021_2f86d24103.pdf)
- [TCG TPM v2.0 Provisioning Guidance](https://trustedcomputinggroup.org/wp-content/uploads/TCG-TPM-v2.0-Provisioning-Guidance-Published-v1r1.pdf)
- [Microsoft: How Windows uses the TPM](https://learn.microsoft.com/en-us/windows/security/hardware-security/tpm/how-windows-uses-the-tpm)
- [Microsoft: GetSystemIdForPublisher](https://learn.microsoft.com/en-us/uwp/api/windows.system.profile.systemidentification.getsystemidforpublisher) e [SystemIdentificationSource](https://learn.microsoft.com/en-us/uwp/api/windows.system.profile.systemidentificationsource)
- [Microsoft: Autopilot requirements](https://learn.microsoft.com/en-us/autopilot/requirements?tabs=networking) e [FAQ](https://learn.microsoft.com/en-us/autopilot/faq)
- [Microsoft: requisiti di Windows 11](https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements) e [dispositivi non conformi](https://support.microsoft.com/en-us/windows/installing-windows-11-on-devices-that-don-t-meet-minimum-system-requirements-0b2dc4a2-5933-4ad4-9c09-ef0a331518f1)
- Fonti non ufficiali su `OfflineUniqueID*`: [Sysnative](https://www.sysnative.com/forums/threads/what-is-the-offlineuniqueidekpub-context.41840/), [slipstream](https://mastodon.social/@slipstream/99514497819803181)

**System76**

- [firmware-open](https://github.com/system76/firmware-open): modelli, `me.rom`, `coreboot.config`
- [Documentazione Intel ME di firmware-open](https://github.com/system76/firmware-open/blob/master/docs/intel-me.md)
- [Il loro fork di coreboot](https://github.com/system76/coreboot): `src/mainboard/system76/mtl`, `src/mainboard/system76/meer9`
- [System76: cos'è l'Intel ME](https://system76.com/support/articles/intel-me/)
- [System76: aggiornamenti firmware di giugno 2023](https://system76.com/blog/post/major-updates-for-system76-open-firmware-june-2023/)
- [CL 52800](https://review.coreboot.org/c/coreboot/+/52800): `me_state`

**Chip e T48**

- [DigiKey: W25Q256JWPIQ, WSON 6x5](https://www.digikey.com/en/products/detail/winbond-electronics/W25Q256JWPIQ/15182111) e [W25Q256JWEIQ, WSON 8x6](https://www.digikey.com.br/en/products/detail/winbond-electronics/W25Q256JWEIQ-TR/15181820)
- [Database di minipro](https://gitlab.com/DavidGriffith/minipro)
- [Manuale XGecu T48](https://manuals.plus/xgecu/t48-universal-ic-programmer-manual) e [manuale TL866II](https://www.hadex.cz/spec/m545b.pdf)
- [Discussione su `/WP` a massa con 25Q256JW](https://forum.reveltronics.com/viewtopic.php?p=4100)
