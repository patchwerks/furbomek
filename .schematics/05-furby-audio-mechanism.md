# Sheet 05 — Furby audio and mechanism

Companion drawing: [05-furby-audio-mechanism.svg](./05-furby-audio-mechanism.svg)

## Scope boundary

The drawing intentionally separates three things:

1. a **patent-described 1998-era embodiment**;
2. **actual-unit unknowns** that require inspection and measurement;
3. the **project proposal** for TTS, OBS program audio, local playback, and face timing.

None of the patent blocks proves that the installed modified head contains the same processor, speaker, position wheel, board, or wiring.

## Patent-described audio path

[US6544098B1](https://patents.google.com/patent/US6544098B1/en) describes an information processor communicating over D0-D3 and CTS with a Texas Instruments TSP50C04 speech coprocessor. The cited embodiment uses LPC speech synthesis, an internal 10-bit DAC, and a 32-ohm speaker. It also describes speed/pitch bytes and LPC data in “say” tables. The patent does not establish a separate external audio-amplifier IC.

Architecture shown in the upper lane:

`information processor [101] -> D0-D3 + CTS [102] -> TSP50C04 LPC/DAC [103] -> 32-ohm speaker [104]`

Community repair material reports a roughly 40 mm, 0.25 W, 32-ohm speaker in some original units and warns that the front tickle/speaker assembly may share a multi-wire connector ([Adopt-a-Furby guide](https://www.adoptafurby.com/furbyinfo/speaker.php)). Treat those values as generation/model dependent.

## Patent-described movement/position lane

The same original-era patent family describes a reversible motor, gear/cam shaft, coordinated eyes/eyelids/beak/ears/body motion, and an optical position wheel in the cited embodiment ([US6149490A](https://patents.google.com/patent/US6149490A/en), [US6497607B1](https://patents.google.com/patent/US6497607B1/en)). The installed unit looks compatible with a coupled mechanism, but its generation, sensor presence, and cam phase are unconfirmed.

`motor drive [111] -> reversible motor [112] -> gear/cam shaft [113] -> coupled face [114]`

`position wheel/sensor [115] -> information processor [101]` is patent-described, not confirmed on this unit.

## Project audio proposal

The project does not depend on factory speech electronics. The conversation/TTS service produces decoded PCM and one authoritative timestamp stream. That stream fans out to:

- OBS program audio/recording;
- local robot playback through a measured amplifier/transducer path;
- energy/viseme events for the bounded face adapter;
- the avatar, so failover keeps the same voice and timing.

Bluetooth playback is acceptable only as a provisional listening path; variable transport latency makes it unsuitable as the master face-sync clock.

### Factory speaker reuse: TBD

Reuse is disabled until the actual transducer is identified:

1. remove power and photograph the label, connector, wire colors, diameter, depth, and mounting;
2. isolate speaker conductors from tickle/sensor conductors;
3. measure unpowered DC resistance (not expected to equal nominal impedance exactly);
4. trace whether the existing drive is single-ended or bridged; never ground an unknown bridged output with an earth-referenced scope clip;
5. test the selected amplifier into a dummy load first, then begin at very low level/current;
6. if 32 ohms/0.25 W is confirmed, 0.25 W corresponds to about 2.83 Vrms and 89 mA rms; treat those as ceilings, not starting targets.

Do not drive a speaker from GPIO. Do not infer that a class-D module is safe merely because it produces sound at another impedance.

## Generation separation

The [Adafruit 2012 teardown](https://learn.adafruit.com/furby-2012-teardown?view=all) shows removable audio wiring for that different generation only. It cannot prove the original-era or installed circuit. Newer-Furby LCD-eye/audio evidence must remain generation-specific.

## Acceptance evidence

- Board and speaker photographs with markings.
- Connector continuity map and DC resistance.
- Differential speaker waveform and RMS level under current-limited power.
- Amplifier/dummy-load thermal test and distortion/listening test.
- Captured A/V/face timestamps demonstrating one clock and bounded skew.

## Stop conditions

If impedance, conductor identity, bridged topology, or power rating is unknown, use a known external speaker and leave the factory transducer disconnected.
