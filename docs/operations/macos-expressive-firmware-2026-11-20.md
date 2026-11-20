# Expressive firmware installation on macOS

On 2026-11-20 the operator authorized application updates on the Mega and
handheld, confirmed physical POWER OFF and connected both boards by USB.
The Mac released the held bridge before accessing either bootloader.
The candidate was reproduced in two independent AVR builds from the
`codex/expressive-motion-candidate` worktree based on `931d9d5`.

Native arm64 AVRDUDE 7.1 used the established `wiring / m2560` and
`arduino / m328p` methods at 115200 baud. The signatures were `0x1e9801`
and `0x1e950f`. Full flash was read and independently verified on both.
The private recovery files preserve the full original readbacks and the
page-aligned application prefixes necessary to restore the touched pages.

| Board | Verified application bytes | Full flash SHA-256 before | Full flash SHA-256 after |
| --- | ---: | --- | --- |
| Mega | 56,258 | `128af490172cb453ef91512ff07733945d0347bbdb95972a0539b45b24584c34` | `d1ff551bd46346ccbd97ae1d97068c3fae4b3615092fbfb0f0d0bab29445dd92` |
| Handheld | 15,434 | `784640ebe10277e03cf4060766e3ca1645b974b2e79bcfc65807a4ec80df214e` | `48c74f21a0902995a20732604eea4eda4dbb95124db1f477236d86d675a74f48` |

The writes used `-D` and application flash targets only. AVRDUDE verified
each application, then the Mac read both boards again. All declared
application bytes match the candidate. All other flash bytes, including
the boot regions and last-page padding, match their original readbacks.
Mega EEPROM compares byte for byte before and after.

The handheld's reported EEPROM exactly matched the first 1,024 bytes of
its own flash on each side of the write. The 61 changed bytes in the
reported EEPROM therefore reflect the changed application. The handheld's
actual EEPROM is unverified through this bootloader, and those captures
must never be used to restore EEPROM. No EEPROM, fuse, lock or bootloader
write was issued.

The body USB device was absent after the readbacks. The new firmware
answered through the handheld RF path at physical POWER OFF. The reply
reported BOOT, idle, fault 0 and 0.0 V. The host wire mappings for
`poke`, `defensive_brace` and `tuck_preview` are available to the
local acceptance runner. The live Hermes allowlist was kept at its
previous scope.

The [firmware record](../hardware/firmware.json) identifies the installed
images. The [maintenance procedure](robot-wired-maintenance.md) governs
application restoration. Recovery writes must stay within the
newly touched flash pages, with both original full flash reads retained
for verification. No ISP or fuse recovery was attempted.

## First supported motion pass

The operator supported the chassis with all six legs free, unplugged the
body USB and stayed at POWER. At powered idle the handheld reported BOOT,
fault 0 and 8.13 V. ARM-only verified DISARM before any gesture.

| Action | Gateway elapsed | Probe and optical result |
| --- | ---: | --- |
| Active | 1,080 ms | Legs visibly extended. Normal DISARM verified. |
| Poke | 985 ms | Normal DISARM verified. The flashlight view resolves too little of the brief reach to verify the foot path. |
| Defensive brace | 2,686 ms | Movement began, then the host reported `operation_timeout`. STOP was acknowledged with FAULT 4 and no normal DISARM. |
| Tuck preview | — | The pass ended at the brace fault before dispatch. |

The camera recorded brace leg movement and a stopped stance short of the
planned return. A near-front leg region moved about 10 pixels at its peak
relative to the pre-action frame. The oblique image has no metric scale.
The host kept its 2,500 ms action budget and the Mega kept its 3,000 ms
cutoff. The host elapsed time includes protocol and STOP handling.

The operator confirmed physical POWER OFF. The temporary test owner closed,
then the Mac's normal edge opened its read-only bridge and reported
`prepared_waiting_for_robot`. No reset or motion was sent during handoff.
The current profile stays on its previous allowlist.

| Private evidence | SHA-256 |
| --- | --- |
| `powered-supported.mkv` | `be8ef867c4faf16d86a226b79331cd9fbbaf5e06bd9dc12be18815b496213b3c` |
| `expressive-supported-pass.jsonl` | `91453db586d39cd2e81c4281a6e0c6ac846cfd7430a2a8a253e5462843924068` |
