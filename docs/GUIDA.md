# Guida all'installazione

Nulla di questa procedura è stato ancora eseguito fino in fondo. I passi 1 e 3 sono stati fatti, i passi di scrittura no.

Ogni passo ha un controllo: se fallisce, ci si ferma.

## 0. Prerequisiti

- XGecu T48 con Xgpro 13 su un secondo PC Windows, e adattatore WSON-8 della misura giusta.
- Dump in `backup/` copiati su un disco esterno, leggibile dal secondo PC.
- Chiavetta con una distribuzione live.
- Alimentatore collegato durante ogni scrittura.
- Licenza di Windows collegata all'account Microsoft: cambiando firmware può chiedere una nuova attivazione.

## 1. Letture dalla scheda

```sh
sudo bash tools/lettura.sh
```

Non scrive sul chip. **Controllo:** ME status `90000255` e le due letture con lo stesso hash. Se non è `90000255`, coreboot non è installabile.

## 2. Recupero col T48

Il T48 non è obbligatorio per scrivere: si può flashare dall'interno. È però l'unico modo di recuperare la scheda se non si riavvia, quindi deve essere pronto prima della prima scrittura.

Minimo indispensabile: chip identificato, adattatore giusto in mano, Xgpro funzionante sul secondo PC, dump sul disco esterno. La prova di lettura qui sotto è la via più sicura, ma richiede di aprire e, per l'adattatore, dissaldare.

1. Aprire la macchina e guardare il chip: marking `W25Q256JW` e misura del WSON-8.
2. In Xgpro scegliere `W25Q256JW @WSON8`, che usa 1,8 V. Non usare mai una voce a 3,3 V.
3. Leggere il chip a macchina spenta, batteria e alimentatore staccati.
4. Se il chip viene dissaldato, usare l'adattatore WSON-8 sul T48. La voce `@ISP` esiste, ma sulla scheda l'alimentazione può raggiungere altri componenti, quindi è la via meno pulita.

**Controllo:** leggere due volte, con lo stesso hash. Il contenuto deve coincidere con `fresh1.bin`, salvo piccole zone di dati del ME e del BIOS. Provare a scrivere e rileggere lo stesso contenuto prima di procedere.

## 3. Immagine con Boot Guard disattivato

Ripetere il dump poco prima, così l'immagine contiene i dati attuali. Procedura in [REPLICARE.md](REPLICARE.md).

**Controllo:** con `tools/confronta-regioni.py`, descriptor, DevExp2 e BIOS devono risultare identici al dump.

## 4. Scrittura di Boot Guard off

Con il T48, a macchina spenta, immagine intera `out-bgoff.bin`: è la via più prudente, perché il ME aggiorna la propria regione mentre la macchina è accesa.

Dall'interno, con la sola regione ME, subito dopo un dump nuovo, a sistema fermo e con l'alimentatore collegato. `flashrom` segnala "SPI Configuration is locked down": le regioni risultano scrivibili, ma la conferma arriva solo alla prima scrittura vera.

```sh
sudo modprobe -r spi_intel_pci spi_intel
sudo flashrom -p internal --ifd -i me -N -w out-bgoff.bin
```

**Controllo:** il BIOS originale parte, Linux e Windows partono, e in `MSR 0x13A` il verified boot non risulta più attivo. Prima era `0x30000006f`.

Se non parte: col T48, riscrivere il dump originale.

## 5. Preparazione

- Salvare un nuovo dump, che diventa il riferimento per tornare indietro con Boot Guard già disattivato.
- Annotare le voci di avvio con `efibootmgr`.

## 6. Scrittura di coreboot

```sh
sudo modprobe -r spi_intel_pci spi_intel
sudo flashrom -p internal --ifd -i bios -N -w coreboot.rom
```

Il primo avvio può durare minuti per l'addestramento della RAM: non interrompere.

## 7. Primo avvio

Nelle variabili UEFI nuove non ci sono voci di avvio. Entrambe le ESP hanno `BOOTX64.EFI`, quindi può partire Windows invece di CachyOS. Da CachyOS:

```sh
sudo efibootmgr -c -d /dev/nvme0n1 -p 4 -L CachyOS -l '\EFI\BOOT\BOOTX64.EFI'
sudo efibootmgr -c -d /dev/nvme0n1 -p 3 -L Windows -l '\EFI\Microsoft\Boot\bootmgfw.efi'
```

Da verificare, in quest'ordine:

| Prova | Comando o azione |
|---|---|
| Windows si avvia | È il primo test: il port è provato solo con Linux |
| NVMe | Un revisore segnala una root port non trovata |
| TPM | `ls /dev/tpm0` e Gestione TPM su Windows |
| HECI spento | `/dev/mei0` assente |
| Tastiera e touchpad, incluse le combinazioni Fn | Prova manuale |
| Luminosità | Tasti Fn, su Linux e Windows |
| Batteria, coperchio, sospensione S3 | Prova manuale |
| Wi-Fi AX210, Ethernet, audio, HDMI/DP | Prova manuale |
| Video | `vainfo`, perché `mei_gsc_proxy` può servire alla decodifica |
| USB-C e Thunderbolt | Instabili anche col BIOS originale |

## 8. Tornare indietro

- **Il sistema parte ancora:** riscrivere la sola regione BIOS del dump.
  ```sh
  sudo modprobe -r spi_intel_pci spi_intel
  sudo flashrom -p internal --ifd -i bios -N -w fresh1.bin
  ```
- **Non parte:** T48 col dump completo.

Il firmware EC sta dentro l'IT5571 e non è toccato da nessuno di questi passi.
