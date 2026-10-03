# Wave 1: checked-in runtime

Observer: repo_current. Inspected HEAD `98fd3d2b1679200ca589c4d5fa11c758166f64bd`, source files, manifests, history and camera/OBS/perception search variants.

Observed `app.vue:200-202,238-240` calls `getUserMedia` with `video: false`; `:207-208` enumerates audio devices only; `:265` visualizes microphone frequencies. `src/chat/openai-assistant.ts:47-59` sends text strings. TTS clients and `server/tts-proxy.js` handle speech. No checked-in camera capture, depth, tracker, GPU visual renderer, OBS worker or robot gateway. `PLAN.md:488` and `.schematics/06-eye-camera-integration.md:17` document the external OBS camera baseline; they do not demonstrate it in this app.

EXPAND: actual camera/OBS device measurements needed before claiming live installed capability; renderer requires a new capture/process/control seam. Closed dead end: existing MediaStream/MediaRecorder and visualizer are audio-only.
