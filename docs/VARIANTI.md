# Le ROM e come passare dall'una all'altra

Aggiornato il 2026-11-11. **Nessuna delle tre è mai stata scritta sul chip.** Valgono le [regole della guida](GUIDA.md#11-procedura-passo-per-passo): prima Boot Guard off e il recupero col T48.

## Le ROM

| ROM | Cartella | sha256 | TPM | Windows | Linux |
|---|---|---|---|---|---|
| coreboot + edk2 | `rom/edk2-senza-tpm` | `a606563b…` | Spento | Sì, aggiornamenti delle versioni non garantiti | Sì |
| coreboot + edk2, senza fix Thunderbolt | `rom/edk2-senza-tpm-senza-fix-thunderbolt` | `ecc0d05c…` | Spento | Come sopra | Sì. Ripiego se USB-C o Thunderbolt peggiorano con la patch `0004` |
| coreboot + edk2 con TPM | `rom/edk2-con-tpm` | `774d484b…` | PTT, boot misurato | Sì, con BitLocker e aggiornamenti | Sì |
| coreboot + edk2 con TPM, senza fix Thunderbolt | `rom/edk2-con-tpm-senza-fix-thunderbolt` | `392aa100…` | PTT, boot misurato | Come sopra | Sì. Ripiego della versione con TPM |
| coreboot + Heads | `rom/heads-con-tpm-sperimentale` | `991c9704…` | PTT, boot misurato | **No** | Sì, verificato da Heads |

Hash completi in `config/rom-conosciute.txt`. Le cartelle stanno in `rom/` nella cartella di lavoro locale, con un `LEGGIMI.txt`. Tutte hanno microcode `0x2b`, tasti luminosità e HECI spento, e la patch Thunderbolt `0004` c'è in tutte tranne le due "senza fix". Le quattro edk2 escono da `tools/build.sh` con `VARIANTE=tpm` e `SENZA_FIX_TB=1`, in tutte le combinazioni.

La ROM edk2 con TPM è la build principale più `patches/opzionale/0003` e il TPM acceso in edk2, con `VARIANTE=tpm tools/build.sh`. Dal 2026-11-11 la `0003` aggiunge le select del TPM in una seconda definizione di `BOARD_SPECIFIC_OPTIONS`, quindi si applica con o senza la `0004`. Ricompilata con questa versione, `edk2-con-tpm` è uscita identica bit per bit. La config differisce da quella principale solo nelle voci del TPM. Microcode, FSP-S, VBT e DSDT sono identici a `rom/edk2-senza-tpm`. FSP-M cambia solo perché viene rilocato a un altro indirizzo della CBFS, e il bootblock perché contiene il boot misurato. edk2 include `Tcg2Dxe`, quindi Windows vede il TPM. Il supporto a Secure Boot c'è come nella build principale: chiavi caricate, Secure Boot spento finché non lo si accende.

Il TPM acceso riporta l'identificativo di PTT, che la build principale toglie ([sezione 10](GUIDA.md#10-tpm-spento)).

## Windows con Heads: cosa dice la comunità

Ricerca del 2026-11-11. **Non esiste un modo di avviare Windows direttamente da Heads.** Windows parte solo da un firmware UEFI, mentre Heads avvia i sistemi con `kexec`, che carica solo kernel Linux.

| Tentativo | Stato |
|---|---|
| Avviare `bootmgfw.efi` con `kexec` | `kexec` non carica eseguibili EFI, e dopo `ExitBootServices()` mancano i servizi che il boot manager usa ([Trammell Hudson](https://trmm.net/chainload/), autore di Heads) |
| Lanciare con `kexec` un edk2 `UefiPayloadPkg`, come fa `uefiboot` di u-root | Dimostrato su QEMU e su pochi server tra il 2019 e il 2021. Fornisce solo un'imitazione di SMM, quindi manca la NVRAM UEFI vera. Mai entrato in Heads ([OSFC 2019](https://osfc.io/2019/talks/booting-windows-on-linuxboot/), [patch edk2 del 2021](https://listman.redhat.com/archives/edk2-devel-archive/2021-July/037330.html), [lista LinuxBoot](https://groups.google.com/g/linuxboot/c/hEUAF-iG64I)) |
| Linux dentro il firmware UEFI che poi restituisce il controllo a Windows (safeboot-loader) | Prototipo in bozza, provato soprattutto su QEMU. Va nella direzione opposta: il firmware resta UEFI, non Heads ([trmm.net](https://trmm.net/chainload/)) |
| Emulatore UEFI dentro `kexec` | Proposto nel 2024 solo per avviare Linux, respinto dal manutentore EFI del kernel ([kexec, ottobre 2024](https://lists.infradead.org/pipermail/kexec/2024-October/030923.html)) |
| Dasharo, la distribuzione commerciale di coreboot con Heads | La variante Heads per portatili supporta solo Linux. Passare tra UEFI e Heads significa riscrivere il firmware ([3mdeb](https://shop.3mdeb.com/product/dasharo-corebootuefi-pro-package-upgrade-to-corebootheads-for-laptop-users/), [Dasharo](https://docs.dasharo.com/unified/novacustom/firmware-transition/)) |

Le strade praticabili restano due: **cambiare firmware** quando serve Windows, oppure **Windows in macchina virtuale** sotto il Linux avviato da Heads.

## Cambiare firmware: `tools/cambia-firmware.sh`

Tutte le ROM hanno **la stessa FMAP**. Lo script riscrive quindi solo la regione `WP_RO`, cioè FMAP e firmware, 13,4 MiB, e lascia com'erano:

- `SMMSTORE`: le variabili UEFI di edk2, con le voci di avvio di Windows e di CachyOS e le chiavi di Secure Boot;
- `RW_MRC_CACHE`: l'addestramento della RAM;
- ME, con Boot Guard disattivato, e descriptor.

Prima di scrivere controlla che l'hash della ROM sia in `config/rom-conosciute.txt` e salva una copia completa del chip. Usa `flashrom` su CachyOS o `flashprog` nella shell di Heads.

```sh
sudo tools/cambia-firmware.sh /percorso/di/rom/edk2-con-tpm/x210ai-edk2-con-tpm.rom    # verso edk2, per Windows
sudo tools/cambia-firmware.sh /percorso/di/rom/heads-con-tpm-sperimentale/x210ai-heads-con-tpm-sperimentale.rom    # di nuovo Heads
```

**Provato il 2026-11-11 sul chip emulato da flashrom**, partendo dal dump originale della scheda: dopo il cambio `WP_RO` coincide con la ROM e il resto del chip è identico byte per byte, sia andando verso Heads sia tornando a edk2. Una ROM non elencata viene rifiutata. Mai provato sul chip vero né dalla shell di Heads.

### Il giro per una sessione di Windows

1. Da CachyOS avviato con Heads: `sudo tools/cambia-firmware.sh .../x210ai-edk2-con-tpm.rom`, poi spegnere e riaccendere.
2. edk2 avvia Windows o CachyOS: si sceglie dal menu di avvio.
3. Finito con Windows: riavviare in CachyOS, che parte anche con edk2, e rimettere Heads con lo script.

Due scritture per sessione, ciascuna di un minuto o due. Si può anche restare su edk2 per giorni e tornare a Heads quando conviene.

### Cosa aspettarsi, da verificare alla prima prova

| | Atteso | Perché |
|---|---|---|
| Voci di avvio e Secure Boot | Conservate | `SMMSTORE` non viene toccata |
| BitLocker | Chiave di ripristino alla prima volta, poi niente | edk2 è sempre la stessa ROM, quindi i PCR misurati tornano uguali |
| TOTP di Heads | Valido al ritorno | Heads è sempre la stessa ROM, quindi stesse misure. Se il codice non torna, il firmware è cambiato: è proprio ciò che Heads deve segnalare |
| Usura della flash | Trascurabile | Circa 100.000 cicli per settore, due per sessione di Windows |
| Rischio | Corrente che manca durante la scrittura | Alimentatore collegato. Si recupera col T48 |

**Non usare** il menu "aggiorna firmware" di Heads per tornare a edk2. Scrive tutta la regione BIOS (`CONFIG_FLASH_OPTIONS`) e cancellerebbe le variabili UEFI. Il cambio funziona solo finché PR0 resta spento in Heads, com'è ora.

## Windows in macchina virtuale

Sotto il Linux avviato da Heads: QEMU/KVM con un TPM virtuale (`swtpm`) e firmware OVMF. Windows 11 26H2 vi si installa senza problemi di requisiti.

- **Pro:** niente scritture sulla flash, Heads resta sempre attivo.
- **Contro:** grafica lenta senza passaggio della GPU (su Meteor Lake servirebbe SR-IOV della grafica integrata, non provato qui), batteria peggiore, e la licenza va riattivata per la macchina virtuale. Non conviene avviare nella VM l'installazione fisica di Windows: driver diversi e BitLocker.

## Quale scegliere, usando soprattutto Linux

| Se interessa | Firmware di tutti i giorni | Per Windows |
|---|---|---|
| Semplicità | edk2 con TPM | Si sceglie dal menu di avvio |
| Le verifiche di Heads | Heads | `cambia-firmware.sh` verso edk2 con TPM, poi di nuovo Heads |
| Mai scrivere sulla flash | Heads | Macchina virtuale |
| Nessun identificativo TPM | edk2 senza TPM | Menu di avvio, con i limiti della [sezione 10](GUIDA.md#10-tpm-spento) |

In ogni caso, la prima ROM da scrivere resta `rom/edk2-senza-tpm` o `rom/edk2-con-tpm`, per un primo avvio con edk2. Heads si prova solo dopo.
