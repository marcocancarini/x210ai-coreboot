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
| Thunderbolt | La review propone `rp1` e `pmc_mux`, funziona solo a volte | **Non applicata:** col BIOS originale qui la porta è `07.0`, cioè `rp0` |
| USB-C intermittente | Aperto, anche col BIOS originale | Da osservare |
| Root port PCIe non trovata | Aperto | Da provare |
| Microcode | ROM con `0x28`, sistema con `0x2b` | Linux lo aggiorna con ogni probabilità; da includere in una build futura |

## Immagine Boot Guard off

Costruita con MFIT 18.1.18.2749, mai scritta.

- Descriptor, DevExp2 e BIOS identici al dump.
- La modifica in sé è di 3 byte nella struttura `$UEP` a `0x448000`: `0x448053` passa da `0xD8` a `0x18`, gli altri due sembrano un checksum. Interpretazione dedotta dai byte.
- MFIT riscrive comunque altri dati del ME, circa 4.670 byte in 12 blocchi, soprattutto metadati di build in `CDMD`.
- Riscomponendo la ricostruzione di controllo, i moduli firmware risultano uguali e la config cambia solo nell'etichetta dell'harness (`#70` diventa `#88`).
- I 518 byte in `0x449000` sono una vecchia copia di UEP che MFIT azzera, e il dump differisce anche per il byte `0x448058`: [analisi](GUIDA.md#modifiche-di-mfit).
- **Punti aperti:** funzione di `0x448058`, e la 18.1 non è provata su questa scheda. L'autore ha usato la 18.0.10.2285.

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

Non per ora. Non esiste una scheda X210AI, il kernel delle schede Meteor Lake non ha btrfs e qui `/boot` è su btrfs, non avvia Windows, ed esclude edk2 nella stessa immagine. Il riferimento è `novacustom-v540tu`.
