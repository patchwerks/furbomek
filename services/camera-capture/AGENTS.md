# Camera-capture agent contract

Agents operate this service for the user. Read root `AGENTS.md`,
`tools/kinect2/AGENTS.md` and `docs/operations/kinect2-host.md` before changes.

- This native service is the sole physical Kinect v2 owner. It must remain
  independent of the Nuxt app, Hermes tool execution and robot actuation.
- Build through `tools/kinect2/build-host.sh`; generated binaries and pinned
  upstream libraries live outside Git under `/data/furbomek-media`.
- Run as the desktop user. `70-furbomek-kinect2.rules` grants active-seat
  `uaccess` with mode `0660`, not world-writable USB access. Keep the installed
  `/etc/udev/rules.d` copy under etckeeper and the authoritative rule here.
- Native depth/IR are 512×424; RGB is 1920×1080. Registration uses factory
  calibration. Never describe interpolated/RGB-derived samples as extra measured
  depth resolution. Reject invalid/non-finite depth and keep occlusion holes.
- `latest.bin` ABI: little-endian uint32 magic `0x32434b46`, version `1`,
  publication sequence, slot count, followed by 16 float32 values per slot:
  row-major Godot Transform3D plus RGBA. Change all consumers when changing ABI.
  Do not bake the first bring-up's 54,272 subsampled slots into future consumers.
- Publish complete frame artifacts atomically in an owner-only directory. RGB,
  point geometry, tracking metadata and crop coordinates must share explicit
  frame identity and timestamp semantics; host receipt is not sensor latency.
- Tracking is an advisory media consumer. It gets frames, not camera ownership,
  Hermes credentials, stream keys, network control or motion authority.
- `track.py` runs with `uv run --no-project --python /usr/bin/python3.12` and its
  pinned script metadata. `vision_frames.py` parses the producer boundary;
  `detect_targets.py` contains real pose/face, ORB-template and depth-region logic.
  `build-host.sh` fetches and verifies the two versioned MediaPipe models and
  resolves the Python environment; no system Python packages are modified.
- Full resolution is 217,088 slots. Four `frame-N.bin` hard-linked snapshots and
  `frame-N.jpg.bin` / `frame-N.optical.bin` JPEG wrappers plus `frame-N.map.bin`
  carry matching sequence prefixes. Native RGB is 1920×1080, registered RGB is
  512×424. `metadata.json` publishes completed ring filenames. The tracker rejects
  overwritten/mixed or more-than-600ms-old inputs before publishing `tracking.json`.
- Each track has explicit kind, ID, score type, source ROI, native optical ROI,
  measured ROI samples and an actual measured probe. Never call a nearest-depth
  component a person or claim ORB confidence is a calibrated probability.
- The actual robot has an agent-seeded private ORB template at
  `/data/furbomek-media/models/robot-template.png`, derived from an observed live
  registered image, plus an equally sized annotated `robot-template-mask.png`
  defining the actual object rather than background corners. ORB features and
  the homography-warped data ROI use this mask. Its stable ID is `object-furbomek`.
  Do not commit either image. If it is
  absent or no longer matches, inspect current real optical/registered frames and
  reseed the actual robot ROI as an agent operation; never force a fixed box or
  pretend a match. Removing the template must remove the object lock; restoration
  must reacquire it. Body/face are separately model-detected, not robot identity.
- Missing calibrated color mappings are represented by `optical_box=null` and
  `probe_optical=null`, never `(0,0,1,1)` or a box centre substituted as a measured
  point. Agents must test an all-unmapped calibration case: valid measured XYZ
  stays available while color-mode brackets, probe and both crops stay hidden.
- Validate with a warning-clean native build and actual sustained non-root
  capture. Inspect RGB, IR, depth, registered color, invalid-depth handling and
  renderer output; USB enumeration alone is not a capture pass.
- Preserve private logs/recordings outside Git, record exact commands/evidence
  and rollback in the operations record, and update agent guidance when ownership
  or deployment assumptions change. Do not make the user perform agent runbooks.
