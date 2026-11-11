# Heads su Meteor Lake: X210AI a confronto con le NovaCustom

Analisi del 2026-11-11. Mette a confronto la [variante Heads di questa repo](HEADS.md) con le uniche due schede Meteor Lake supportate da Heads, NovaCustom V540TU e V560TU. Le fonti sono l'albero di Heads al commit `b8acd828`, le config di coreboot di entrambe le schede, la documentazione di Dasharo e i report della comunità Qubes.

## In breve

- **Le basi sono le stesse.** Stessa piattaforma, stesso FSP, stesso kernel di Heads (6.1.8), stesso framebuffer GOP e stesso boot misurato di coreboot. La V540TU e la V560TU differiscono tra loro solo nel nome della config.
- **PTT in Heads non è una novità.** Le schede MSI Z690 e Z790 di Heads, desktop Alder e Raptor Lake in stato "Active", usano già `HAVE_INTEL_PTT` e `CRB_TPM` come la nostra variante.
- **La differenza decisiva è Boot Guard.** Sulle NovaCustom è attivo con la chiave del produttore, e l'ACM di Intel misura il primo blocco del firmware in PCR 0 prima che giri qualsiasi codice di coreboot. Qui Boot Guard va disattivato per poter usare coreboot. La radice della catena di misure diventa così il bootblock, che sta nella flash, e un bootblock modificato può falsificare le misure successive. Il TOTP di Heads vale quindi solo finché nessuno ha potuto scrivere sulla flash.
- **Le protezioni della flash mancano.** La V540TU blocca la flash dal controller SPI e attiva il lockdown del chipset. La nostra variante per ora non blocca nulla, per poter cambiare firmware. È la prima cosa da sistemare, proprio perché manca Boot Guard.
- **La protezione DMA precoce manca anche alle NovaCustom.** Dasharo non riesce ad attivarla su Meteor Lake, e l'ha spenta il 2025-09-23 ([issue 985](https://github.com/Dasharo/dasharo-issues/issues/985)).

## Confronto

| | NovaCustom V540TU / V560TU | X210AI, variante sperimentale |
|---|---|---|
| Stato in Heads | "Active", tester assegnati ([BOARDS_AND_TESTERS](https://github.com/linuxboot/heads/blob/master/BOARDS_AND_TESTERS.md)), release commerciali Dasharo v0.9.0 e v0.9.1 | Fuori dall'albero di Heads, costruita il 2026-11-11, mai avviata |
| coreboot | Fork Dasharo basato su 24.12 (`dasharo_v56`) | Fork WheeledCord, port non ancora upstream ([CL 94886](https://review.coreboot.org/c/coreboot/+/94886)) |
| FSP | ArrowLake IoT UH, MTL-H | Stesso pacchetto |
| Kernel di Heads | 6.1.8, `linux-novacustom-common` | La stessa, più `TCG_CRB` e `BTRFS_FS` |
| Video in Heads | Framebuffer GOP di FSP | Uguale |
| TPM | TPM 2.0 discreto su eSPI (TIS) | PTT dentro il ME, via CRB |
| Attacco del reset GPIO del TPM | Non vulnerabile, il TPM è su eSPI ([doc Heads](https://github.com/linuxboot/heads/blob/master/doc/TPM_GPIO_Reset_Approaches.md)) | Non si applica: PTT non ha una linea di reset esterna |
| Boot Guard | Attivo, chiave NovaCustom fusa nei FPF, ACM e manifest firmati nella ROM ([doc IBB](https://github.com/linuxboot/heads/blob/master/doc/ibb-measurement.md)) | **Disattivato**, ed è l'unico modo di usare coreboot qui |
| Chi misura per primo | L'ACM di Intel, in hardware, su PCR 0 | Il bootblock di coreboot, che misura se stesso |
| ME | ME di Dasharo, con HAP (`HAVE_INTEL_ME_HAP`) | ME del produttore, acceso, HECI spento. HAP non va toccato su questa scheda ([guida](GUIDA.md#il-bit-hap-su-meteor-lake)) |
| Descriptor e ME nella ROM | Sì (`HAVE_IFD_BIN`, `HAVE_ME_BIN`) | No: si scrive solo la regione BIOS |
| Regioni scritte da Heads | `--ifd -i bios -i me -i fd` | `--ifd -i bios` |
| Blocco della flash da coreboot | `BOOTMEDIA_LOCK_CONTROLLER` + `BOOTMEDIA_LOCK_WHOLE_RO` | `BOOTMEDIA_LOCK_NONE` |
| Scritture della flash solo da SMM, lockdown | `SPI_FLASH_SMM`, `SOC_INTEL_COMMON_SPI_LOCKDOWN_SMM`, `HAVE_INTEL_CHIPSET_LOCKDOWN` | No |
| PR0 prima di `kexec` | Sì (`FINALIZE_PLATFORM_LOCKING`) | No, finché non è provata |
| Protezione DMA precoce (VT-d PMR) | Selezionata, ma spenta per Meteor Lake il 2025-09-23: "VT-d PMR HOB not found" ([issue 985](https://github.com/Dasharo/dasharo-issues/issues/985)) | No: nel nostro fork Meteor Lake non seleziona nemmeno `SOC_INTEL_COMMON_BLOCK_VTD` |
| IOMMU nel kernel di Heads | `INTEL_IOMMU_DEFAULT_ON` | Uguale |
| Thunderbolt/USB4 | Driver dei retimer (`DRIVERS_INTEL_USB4_RETIMER`) | Patch `0004` su RP1, GPIO della retimer ignoto. Il kernel di Heads non ha `USB4` |
| EC | EC Dasharo, aggiornabile da Heads (v0.9.1) | EC a parte ([x210ai-ec](https://github.com/marcocancarini/x210ai-ec)), non gestito da Heads |
| GbE | Sì, con randomizzazione del MAC | Nessuna regione GbE |
| Windows | Non supportato dalla variante Heads | Uguale: serve il cambio di firmware ([VARIANTI.md](VARIANTI.md)) |

## Problemi noti delle NovaCustom che probabilmente riguardano anche noi

Dalle note di rilascio Heads della V540TU ([Dasharo](https://docs.dasharo.com/variants/novacustom_v540tu/releases_heads/)) e dalle issue collegate:

| Problema | Riguarda anche l'X210AI? |
|---|---|
| Avvio di Heads lento, "dozens of seconds", perché mancano gli MTRR per la cache della flash ([issue 1336](https://github.com/Dasharo/dasharo-issues/issues/1336)) | Probabile: stessa piattaforma. Dasharo l'ha chiusa con la v0.9.1, ma non risulta ancora risolta |
| Protezione DMA precoce non applicabile ([issue 985](https://github.com/Dasharo/dasharo-issues/issues/985)) | Sì, e da noi manca anche la base VT-d |
| Errori inattesi in `dmesg` (issue 1201) | Da vedere al primo avvio |
| Prestazioni più basse delle varianti NVIDIA (issue 1216), "barely noticeable" secondo NovaCustom | Possibile: dipende da coreboot e FSP |
| Un sistema già installato non viene visto come avviabile tornando a edk2 (issue 713) | Non dovrebbe: il nostro cambio di firmware conserva `SMMSTORE`. Da verificare |
| Sospensione S3 | Sulla V540TU con Heads funziona secondo il [report Qubes](https://forum.qubes-os.org/t/novacustom-v54-series-v540tu-dasharo-coreboot-heads/33118). Da noi c'è `HAVE_ACPI_RESUME`, mai provata |

## Cosa significa senza Boot Guard

Con Boot Guard, chi scrive sulla flash un firmware modificato non può falsificare PCR 0, perché la misura la fa l'ACM nel processore. Senza Boot Guard, la prima misura la fa il bootblock stesso. Un bootblock modificato può quindi estendere nei PCR i valori del firmware originale, e il TOTP risulterebbe valido.

Da qui due conseguenze:

1. **Heads qui protegge bene `/boot`** (firme GPG dei kernel e degli initrd) **e il firmware solo se la flash resta protetta.** Contro un attacco da remoto conta che la flash non sia scrivibile dal sistema operativo. Contro chi ha la macchina in mano e una pinza SPI la protezione non c'è: è lo stesso limite delle vecchie schede di Heads senza Boot Guard, come la X230.
2. **Il cambio di firmware per Windows apre una finestra.** Finché gira la ROM edk2 la flash è scrivibile da Windows e da Linux. Il ritorno a Heads non rileverebbe una modifica fatta bene in quel periodo.

## Cosa conviene fare, in ordine

1. **Accendere PR0 in Heads** (`CONFIG_FINALIZE_PLATFORM_LOCKING=y`) dopo un primo avvio riuscito. Il cambio di firmware resta possibile: da Heads verso edk2 si fa dalla shell di recupero di Heads, prima che PR0 venga applicato; da edk2 verso Heads si fa da CachyOS. Va aggiornato il flusso in [VARIANTI.md](VARIANTI.md).
2. **Capire come Dasharo combina `BOOTMEDIA_LOCK_WHOLE_RO` con gli aggiornamenti da Heads** prima di copiarlo. Un blocco messo da coreboot impedirebbe anche a Heads di riscrivere la flash.
3. **Non inseguire la protezione DMA precoce.** Dasharo non ci riesce su Meteor Lake e da noi manca la base VT-d. Contro il DMA da Thunderbolt restano l'IOMMU del kernel e il fatto che Heads non attiva i tunnel USB4.
4. **Usare la variante edk2 con TPM come firmware di tutti i giorni**, se Windows serve spesso. Ogni cambio di firmware indebolisce quello che Heads può garantire.
5. **Prima prova di Heads:** misurare il tempo di avvio (issue 1336), controllare `dmesg`, `tpm2_getcap properties-fixed`, il menu di avvio con `/boot` su btrfs, e la sospensione.

## Punti aperti

- Come si comporta PTT con HECI spento in Heads: lo dice solo il primo avvio.
- Se il fork WheeledCord ha gli MTRR per la cache della flash che mancano a Dasharo.
- Se FSP o la patch `0004` aprono tunnel PCIe sulla porta Thunderbolt prima del sistema operativo.
