# Variante Heads, sperimentale

Aggiornato il 2026-11-11. **Mai costruita con Heads, mai avviata.** La build principale resta coreboot con edk2 e senza TPM. Questa è una seconda ROM, da provare solo dopo.

## Cos'è

[Heads](https://github.com/linuxboot/heads) mette un piccolo Linux nella flash al posto di edk2. Prima di avviare il sistema controlla, con il TPM e una chiave GPG, che firmware e `/boot` non siano cambiati, e lo mostra con un codice TOTP sul telefono o con una chiavetta HOTP. Poi avvia il kernel del disco con `kexec`.

La variante parte da `novacustom-v540tu`, l'unica scheda Meteor Lake di Heads, e usa il fork e le patch di questa repo.

## Cosa cambia rispetto alla build principale

| | Build principale (edk2) | Variante Heads |
|---|---|---|
| Payload | edk2 (UEFI) | Linux 6.1.8 di Heads, con initrd |
| TPM | Spento | **PTT acceso**, via CRB, con boot misurato |
| Windows | Sì | **No**: `kexec` non avvia Windows. Per usarlo va riscritta la ROM edk2 |
| HECI | Spento prima del payload | Uguale |
| Microcode | `0x2b` dal sottomodulo | `0x2b` come file esterni, scaricati e verificati da `build-heads.sh` |
| Regioni scritte | Solo BIOS | Solo BIOS (`CONFIG_FLASH_OPTIONS ... --ifd -i bios`) |
| PR0 (flash bloccata prima di `kexec`) | No | No, per ora: da Linux si può ancora riscrivere la ROM edk2 |

**Il TPM riporta l'identificativo** che la build principale toglie ([sezione 10 della guida](GUIDA.md#10-tpm-spento)): l'EK di PTT è unico e certificabile da Intel. È stata una scelta esplicita per questa variante, il 2026-11-11: senza TPM Heads non ha senso.

## File

| File | A cosa serve |
|---|---|
| `heads/build-heads.sh` | Clona Heads al commit fissato, aggiunge scheda, config e patch, scarica il microcode e lancia la build nel container |
| `heads/x210ai-tpm2-sperimentale.config` | Scheda Heads, ricavata dalla `v540tu` |
| `heads/coreboot-x210ai.defconfig` | Config coreboot minima, la sorgente |
| `heads/coreboot-x210ai.config` | La stessa completata con `olddefconfig`, quella che usa Heads |
| `heads/linux-x210ai.config` | Kernel della `v540tu` con due righe in più: `CONFIG_TCG_CRB=y` per PTT, `CONFIG_BTRFS_FS=y` per `/boot` |
| `heads/heads-modules-coreboot.patch` | Aggiunge a Heads la versione `x210ai` di coreboot, cioè il fork al commit di `versioni.txt` |

Le patch di coreboot sono quelle della repo, copiate in quest'ordine: `0001` luminosità, `0004` Thunderbolt, `opzionale/0003` TPM. La `0003` è stata riallineata il 2026-11-11 perché si applichi dopo la `0004`: prima falliva su `Kconfig`.

## Cosa è stato verificato, senza Heads

Il 2026-11-11, con la toolchain di coreboot già pronta e senza il container di Heads:

- Le tre patch si applicano in ordine sul fork.
- coreboot compila con `coreboot-x210ai.config`. Sono inclusi i driver CRB e PTT. PTT viene rilevato dal registro TXT, non tramite HECI, quindi spegnere HECI non lo ostacola.
- Il microcode esterno è identico byte per byte a quello di `output-4`.
- Il kernel di Heads con la nostra config esce di **3,2 MB**. Compilato con GCC 16 al posto della toolchain di Heads, quindi la misura è indicativa.
- Con quel kernel nella ROM restano **9,0 MB** liberi per l'initrd di Heads. La regione BIOS è di 14 MiB e non si può allargare senza cambiare il descriptor, che non va toccato.

## Cosa non è verificato

| Punto | Perché conta | Come si scopre |
|---|---|---|
| Build in Heads | Serve Docker, che su questa macchina non c'è | `heads/build-heads.sh` dopo aver installato Docker |
| L'initrd ci sta | Se supera 9 MB la ROM non si costruisce | La build lo dice. Se serve, si tolgono moduli come `CONFIG_HOTPKEY` o `CONFIG_LVM2` |
| `/boot` su btrfs | `/boot` è una cartella nel sottovolume `@`, non una partizione. Heads lo prevede poco: la sua guida supporta ext4 e xfs | Al primo avvio, menu di boot di Heads. In alternativa, una partizione `/boot` ext4 separata |
| PTT con HECI spento | La combinazione non è mai stata avviata su questa scheda | `tpm2_getcap properties-fixed` dalla shell di Heads |
| Il kernel 6.1.8 su Meteor Lake | Sulla `v540tu` funziona, su questa scheda mai provato | Primo avvio |
| Valore pratico | Il disco non è cifrato: Heads protegge firmware e `/boot`, non i dati | Decidere se cifrare la root |

## Come si costruisce

Docker va installato una volta, con permessi di root:

```sh
sudo pacman -S docker
sudo systemctl enable --now docker
sudo usermod -aG docker $USER    # poi uscire e rientrare
```

Poi, senza root:

```sh
heads/build-heads.sh /percorso/di/heads
```

La prima build costruisce anche le toolchain di Heads e di coreboot: ore, non minuti. La ROM esce in `build/x86/x210ai-tpm2-sperimentale/`.

## Quando e come provarla

Solo dopo che la build edk2 è partita almeno una volta su questa scheda ([procedura](GUIDA.md#11-procedura-passo-per-passo)), con il recupero col T48 pronto.

1. Da CachyOS, con la build edk2 in funzione: salvare un dump completo.
2. Scrivere solo la regione BIOS:
   ```sh
   sudo modprobe -r spi_intel_pci spi_intel
   sudo flashrom -p internal --ifd -i bios -N -w heads-x210ai-tpm2-sperimentale.rom
   ```
3. Spegnere e riaccendere. Al primo avvio Heads chiede di generare le chiavi e il segreto TOTP: seguire la procedura OEM Factory Reset.
4. Controllare `tpm2_getcap properties-fixed`, la tastiera, lo schermo, il disco NVMe e l'avvio di CachyOS.

**Per tornare a edk2:** da CachyOS avviato con Heads, oppure dalla shell di recupero di Heads, scrivere la regione BIOS della ROM edk2 con lo stesso comando. Funziona finché PR0 resta spento. Se Heads non parte, col T48.

**Non usare** il menu di Heads per aggiornare il firmware con una ROM diversa da questa, e non attivare la randomizzazione del MAC: su questa scheda non c'è regione GbE.
