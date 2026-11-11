# Verifiche e decisioni

Dati raccolti il 2026-11-06 sulla scheda, con BIOS AMI 0.5, ME 18.0.5.2098 e Core Ultra 7 165H (`0xA06A4`).

## Misurato sulla scheda

| Voce | Valore | Significato |
|---|---|---|
| ME status | `90000255` | Manufacturing mode: Boot Guard si può disattivare |
| MSR `0x13A` | `0x30000006f` | Boot Guard attivo |
| Chip SPI | Winbond W25Q256JW, `ef6019` | 32 MiB, 1,8 V |
| Descriptor | `FLMSTR1=ffffffff` | Nessuna regione vietata all'host |
| Protezione del chip | Disabilitata | Da `flashrom --wp-status`, dopo aver scollegato il driver SPI |
| TPM | Driver `tpm_crb_acpi`, CRB a `0xFED40040`, start method 7 | PTT attivo, confermato da `PttSupported=Yes` nella config del ME |
| BitLocker | Assente | `blkid -p`: `TYPE="ntfs"` |
| Pannello | 2560x1600 | L'autore del port ha un 3000x2000 |
| VBT | Identico a `data.vbt` del port | Nessuna patch necessaria |
| Wi-Fi | AX210 | L'autore ha RTL8822BE |
| NVMe | `00:06.0` | Da confrontare con la root port nel primo avvio |
| Thunderbolt | `00:07.0` con ID `8086:7ec5`, DMA0 e DMA1 attivi, due domini | ID di **TBT RP1**, non RP0 |
| Microcode | BIOS `0x1c`, dopo Linux `0x2b` | Da `dmesg`: "Updated early from: 0x0000001c" |

## Compatibilità del T48

Il chip è supportato. Per i pogo pin vedi la [sezione 6 della guida](GUIDA.md#6-dump-col-t48-e-pogo-pin). La lista ufficiale T48 V13.16 del 2026-03-17 elenca `W25Q256JW @WSON8`, `@SOIC8`, `@SOIC16` e `@ISP`.

Nel database di [minipro](https://gitlab.com/DavidGriffith/minipro), che copia quello di Xgpro, la voce ha `chip_id=0x00ef6019` e `voltages=0x0206`. Il valore `0x06` nella tabella Vcc del T48 corrisponde a 1,8 V; la W25Q256JV a 3 V ha `0x08`. Il chip ID coincide con quello letto dal kernel.

Da controllare a mano: la misura del package, perché `@WSON8` non la indica, e se l'adattatore in possesso è quello giusto. L'adattatore 17-in-1 è venduto con WSON8 6x5 e 8x6 mm.

## Bug noti

Stato verificato sul commit `f0877e0d3c` e sulla CL 94886, ferma dal 2026-09-08 senza Code-Review, con 8 commenti non risolti al 2026-11-07.

| Problema | Stato | Qui |
|---|---|---|
| Immagine Boot Guard precompilata | Rimossa, ma il README del fork la cita ancora | Non usarla |
| S3 | Risolto: `INTEL_TME` disattivato | Nessuna azione |
| Tasti luminosità | Mancavano `_Q06` e `_Q07` | **Patch inclusa**. Dal DSDT originale: `_Q06` abbassa, `_Q07` alza |
| TPM | Il port non lo configurava | **Lasciato spento di proposito** dal 2026-11-07: [motivi](GUIDA.md#10-tpm-spento). Patch in `patches/opzionale/` |
| Thunderbolt | Il port abilita `rp0`, la review propone `rp1` e `pmc_mux` | **Patch `0004` inclusa.** La conclusione precedente era sbagliata: col BIOS originale la porta in `07.0` ha ID `8086:7ec5`, che è **RP1**. Compare in `07.0` perché RP0 è spento e la funzione viene rimappata. RP1 corrisponde alla porta TCSS 1 e a DMA0 |
| USB-C intermittente | Aperto, anche col BIOS originale | Da osservare |
| Root port PCIe non trovata | Aperto | Da provare |
| Microcode | Non è un bug: il fork fissa `microcode-20260512` (`0x28`), il pacchetto `intel-ucode` 20260925 ha `0x2b` | **Risolto:** build con `microcode-20260925`, ROM con `0x2b`. Il BIOS originale carica `0x1c` (2024-01-03), che Linux porta a `0x2b` all'avvio |

## Immagine Boot Guard off

Costruita con MFIT 18.1.18.2749 e, il 2026-11-11, con la 18.0.10.2285. Mai scritta.

- Descriptor, DevExp2 e BIOS identici al dump.
- La modifica in sé è di 3 byte nella struttura `$UEP` a `0x448000`: `0x448053` passa da `0xD8` a `0x18`, gli altri due sembrano un checksum. Interpretazione dedotta dai byte.
- MFIT riscrive comunque altri dati del ME, circa 4.670 byte in 12 blocchi, soprattutto metadati di build in `CDMD`.
- Riscomponendo la ricostruzione di controllo, i moduli firmware risultano uguali e la config cambia solo nell'etichetta dell'harness (`#70` diventa `#88`).
- I 518 byte in `0x449000` sono lo slot B di UEP: il record di fabbrica, invalidato dal ME quando ha alzato il flag `0x448058`. MFIT lo cancella. Non è un errore né una vulnerabilità in sé: [analisi](GUIDA.md#i-518-byte-in-0x449000).
- Il "checksum" di UEP è un **CRC-16/CCITT-FALSE** sui byte `+0x06`-`+0x208`, verificato su quattro record. Nessuna firma: è la ragione per cui Boot Guard si disattiva senza chiavi finché i FPF non sono scritti.
- Verifica offline del 2026-11-08 con `tools/uep.py` e `analisi-bootguard.py`: in `out-bgoff.bin` profilo `0x18`, CRC corretto, catena KM, BPM e IBB ancora valida, config diversa dal dump solo in `BtGuardProfileConfig`. Il dump attuale coincide con quello da cui è costruita.
- 2026-11-11, MFIT 18.0.10.2285 eseguita sullo stesso dump. `out-bgoff.bin` ha UEP, FITC, moduli, descriptor e BIOS identici a quella della 18.1. Cambia 1.274 byte rispetto al dump, contro i 4.674 della 18.1. Non tocca la tabella di layout del CSE a `0x4000` e non aggiunge il record `PMC` in CDMD. Catena KM, BPM e IBB valida; ricomposta, la config differisce dal dump solo nel profilo e nell'harness (`#82`): [risultato](GUIDA.md#risultato-del-confronto-2026-11-11).
- **Punti aperti:** funzione di `0x448058`. La 18.1 resta non provata su questa scheda, ma la raccomandazione ora è scrivere l'immagine della 18.0, la stessa versione usata dall'autore.

## Decisioni sul ME

Obiettivo aggiornato il 2026-11-07: **TPM spento** e ME ridotto al minimo. La tabella riporta anche il ragionamento precedente, quando il TPM doveva restare.

| Opzione | Scelta | Motivo |
|---|---|---|
| Rimuovere moduli (`me_cleaner`) | No | Nessun supporto per ME 18. Nella regione ME ci sono anche PMC, Thunderbolt e PHY. Nemmeno System76 lo fa su Meteor Lake: [confronto](GUIDA.md#confronto-con-system76) |
| Bit HAP | No | Offset non confermato su Meteor Lake. `ifdtool -M` non va usato: su questo dump segnala HAP attivo a ME acceso. `0x21E` è solo un candidato non confermato |
| HECI disattivato | **Sì** | `DISABLE_HECI1_AT_PRE_BOOT`. PTT usa CRB, quindi dovrebbe restare: da provare |
| Altre impostazioni di MFIT | No | Immagine Consumer senza AMT, 55 impostazioni in sola lettura |
| `MngHwStatus` | Mai | L'aiuto di MFIT parla di disattivazione permanente via FPF |

## Heads

Rivalutato il 2026-11-08: **no, e il motivo ora è più forte di prima.** Il riferimento resta `novacustom-v540tu`, l'unica scheda Meteor Lake in Heads.

| Requisito di Heads | Qui | Conseguenza |
|---|---|---|
| Un TPM: Heads sigilla i segreti e misura il boot col TPM (TOTP/HOTP) | **TPM spento** dal 2026-11-07 | Senza TPM resta poco più di un bootloader. È la ragione decisiva |
| Kernel della scheda: `linux-novacustom-common.config`, Linux 6.1.8 | `CONFIG_TCG_CRB` non impostato, solo TIS | Anche tornando a PTT, che usa CRB, il TPM non sarebbe visto senza cambiare il kernel |
| Filesystem di `/boot` | Stesso kernel senza `CONFIG_BTRFS_FS`, qui `/boot` è su btrfs | Servirebbe una partizione `/boot` ext4 o un kernel modificato |
| Avvio via `kexec` | Windows non si avvia con `kexec` | Windows andrebbe tolto da questa macchina |
| Nessuna scheda X210AI | Port non accettato upstream | Andrebbe scritta una scheda Heads e mantenuta a parte |
| `v540tu` usa un TPM discreto e un `me.bin` di Dasharo | PTT nel ME, ME del produttore | Nulla da riusare direttamente |

Quando riconsiderarlo: solo se si rinuncia a Windows su questa macchina e si torna a un TPM. Anche allora conviene aspettare che il port sia accettato upstream.

Nota a margine: la config coreboot di `v540tu` imposta `CONFIG_HAVE_INTEL_ME_HAP=y` su Meteor Lake. È un indizio utile per il bit HAP, ancora non confermato qui, ma il valore viene dal `me.bin` di Dasharo e non dal nostro.
