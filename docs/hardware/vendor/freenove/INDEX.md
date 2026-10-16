# Freenove official reference archive

This directory is an unchanged, offline reference collection from the public official repository [Freenove/Freenove_Hexapod_Robot_Kit](https://github.com/Freenove/Freenove_Hexapod_Robot_Kit), pinned to commit `1596c5ffe07a262fa7dc6d0189de6c2321270278` (2026-02-09). Files were extracted from the pristine local clone at `/tmp/opencode/freenove-hermes` using Git blobs, not guessed download URLs. `MANIFEST.sha256` records the resulting bytes; verify it with `sha256sum -c MANIFEST.sha256` from this directory.

Archived and independently verified on 2026-10-15. The collection contains 15
upstream artifacts: 12 PDFs, one firmware ZIP, the upstream README and license.
Each basename is unchanged. Official source paths map as follows:

| Archive directory | Path in the pinned official repository |
|---|---|
| `manuals/`, `battery/`, `calibration/`, `troubleshooting/` | Repository root |
| `schematics/` | `Hardware/` |
| `firmware/` | `ArduinoLibraries/` |
| `upstream/` | Repository root |

The immutable download URL for any source path is
`https://raw.githubusercontent.com/Freenove/Freenove_Hexapod_Robot_Kit/1596c5ffe07a262fa7dc6d0189de6c2321270278/<source-path>`.
These are reference copies, not adaptations. Copyright, attribution, trademark
and license notices inside the original files remain intact; no endorsement by
Freenove is implied.

## Contents

- `manuals/`: V2 and V3 tutorials.
- `battery/`: V2 and V3 battery documents; these contain the vendor's battery handling and safety guidance.
- `calibration/`: V2 and V3 calibration graphs.
- `troubleshooting/`: vendor troubleshooting guide.
- `schematics/`: all five controller schematic revisions present at the pin: FNM0018, FNM0019 V2.0, and FNM0019B V3.0, V3.1, V3.2.
- `firmware/FNHR.zip`: the upstream FNHR firmware archive, preserved without extraction or modification.
- `upstream/`: upstream `readme.md` and `LICENSE.txt`.

PDF sanity checks completed: all 12 PDFs parse with `pdfinfo` and report a positive page count. This is a structural check, not a guarantee that every page is readable or that the documents are safe instructions for this build.

## Evidence and limits

The battery PDFs are the supplied battery/safety references. The schematics are the supplied controller pin and circuit references. The tutorials and troubleshooting guide are vendor references, not authorization to energize the robot. No device was connected or tested, and this archive does not prove which controller revision is installed in the project robot.

The copied firmware remains an unmodified attributed reference artifact. The upstream license is preserved in `upstream/LICENSE.txt`; inspect it before redistribution or execution. In particular, the repository identifies its license as CC BY-NC-SA 3.0. Archiving it here does **not** grant commercial, operational, or derivative-work permission beyond the actual license terms.

## Use the correct revision

The V2.0 schematic has three servo supply groups controlled through A15, A14
and A13. The V3.2 schematic instead shows two groups controlled through A15 and
A14, and a CH340C / USB-C interface. Both specify an ATmega2560 and a 16 MHz
reference clock. This is vendor reference evidence, not a measurement of the
installed board. Do not choose a power-enable pin map merely because the MCU is
known or because a source library mentions three groups.

The original photographs show USB-C and CH340 enumeration, consistent with the
newer family, but the exact PCB revision and electrical behavior remain
unqualified. The new project safety diagnostic does not touch any of these pins.
