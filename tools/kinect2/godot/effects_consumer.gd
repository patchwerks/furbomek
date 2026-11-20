extends Node

const Request = preload("res://effect_request.gd")
const Framing = preload("res://effect_framing.gd")
var viewer: Node
var directory := ""
var consumer_id := ""
var revision := 0
var lease_owner := ""
var cue_id := ""
var effective: RefCounted
var framing := Framing.new()
var expires_at := 0
var started_at := 0
var poll_at := 0
var last_raw := ""
var snapshot: Dictionary = {}
var pulse: ColorRect

func configure(target: Node) -> void:
	viewer = target
	directory = viewer.loader.stream_directory
	consumer_id = Crypto.new().generate_random_bytes(16).hex_encode()
	pulse = ColorRect.new()
	pulse.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	pulse.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pulse.color = Color(0.92, 0.04, 0.08, 0)
	viewer.get_node("Hud").add_child(pulse)
	viewer.loader.snapshot_ready.connect(update_snapshot)
	viewer.loader.snapshot_expired.connect(func(): snapshot = {}; pulse.hide(); publish("source_lost"))
	neutral()
	publish("ready")

func tick() -> void:
	var now := Time.get_ticks_msec()
	if effective != null:
		if now >= expires_at:
			revision += 1
			neutral()
			publish("expired")
		else:
			apply_framing()
			var phase: float = float(now - started_at) / 1000.0 * effective.pulse_hz * TAU
			pulse.color.a = (0.5 - 0.5 * cos(phase)) * float(effective.intensity_percent) / 100.0 * 0.25
			pulse.visible = viewer.source_valid and effective.pulse_hz > 0
	if now < poll_at:
		return
	poll_at = now + 100
	var file := FileAccess.open(directory.path_join("effects.json"), FileAccess.READ)
	if file == null or file.get_length() > 8192:
		return
	var raw := file.get_as_text()
	if raw == last_raw:
		return
	last_raw = raw
	var result := accept(raw)
	publish(result)

func accept(raw: String) -> String:
	var request = Request.parse(raw)
	if request == null:
		return "invalid"
	var age: int = int(Time.get_unix_time_from_system() * 1000) - request.issued_ms
	if request.consumer_id != consumer_id or request.expected_revision != revision or request.revision != revision + 1:
		return "conflict"
	if age < 0 or age > 1000 or age >= request.duration_ms:
		return "expired_request"
	if not viewer.source_valid:
		return "source_unavailable"
	effective = request
	revision = request.revision
	lease_owner = request.owner
	cue_id = request.cue_id
	started_at = Time.get_ticks_msec()
	expires_at = started_at + request.duration_ms - age
	match request.look:
		"rgb.fixed.v1": viewer._set_palette(0)
		"rgb.crimson.v1": viewer._set_palette(1)
		"xyz.depth.v1": viewer._set_palette(2)
		"xyz.crimson.v1":
			viewer._set_palette(1)
			viewer._use_native_view()
	viewer._set_point_pixels(request.point_pixels)
	viewer.yaw = request.yaw
	viewer.pitch = request.pitch
	viewer.zoom = viewer.INITIAL_ZOOM / request.zoom
	viewer._apply_camera()
	viewer.hud.visible = request.hud_visible
	viewer.hud.insets_enabled = request.insets_visible
	viewer.hud.subject_lock = request.subject_id if "subject" in request.rules else ""
	viewer.hud.set_snapshot(snapshot, viewer._palette_name(), request.look == "rgb.fixed.v1")
	viewer.color_surface.set_snapshot(snapshot, viewer.hud.get_selected_track())
	viewer.ports.visible = request.hud_visible
	viewer.hud.set_palette_label(viewer._palette_name())
	apply_framing()
	return "applied"

func update_snapshot(value: Dictionary) -> void:
	snapshot = value
	apply_framing()

func apply_framing() -> void:
	if effective == null:
		return
	viewer.color_surface.crop = framing.resolve(effective, snapshot, int(Time.get_unix_time_from_system() * 1000))
	viewer.color_surface.zoom = 1.0 if effective.look == "rgb.fixed.v1" else effective.zoom
	viewer.color_surface._update_crop()
	if not viewer.hud.subject_lock.is_empty() and framing.matched_id.is_empty() and effective.look != "rgb.fixed.v1":
		viewer.hud.selected = {}
		viewer.hud.processed.hide()
		viewer.hud.optical.hide()
		viewer.hud.queue_redraw()
		viewer.color_surface.shader_material.set_shader_parameter("subject_box", Vector4(-2, -2, 0, 0))
	if not effective.insets_visible:
		viewer.hud.processed.hide()
		viewer.hud.optical.hide()

func manual_override() -> void:
	revision += 1
	effective = null
	lease_owner = "operator"
	cue_id = ""
	pulse.hide()
	viewer.hud.show()
	viewer.hud.insets_enabled = true
	viewer.hud.subject_lock = ""
	framing.crop = viewer.color_surface.get_meta("view_crop", viewer.color_surface.crop)
	framing.matched_id = ""
	framing.reason = "manual_hold"
	viewer.ports.show()
	publish("manual_override")

func neutral() -> void:
	effective = null
	lease_owner = ""
	cue_id = ""
	pulse.hide()
	viewer._set_palette(0)
	viewer.color_surface.crop = Rect2(0, 0, 1, 1)
	framing.crop = Rect2(0, 0, 1, 1)
	framing.matched_id = ""
	framing.reason = "fixed"
	viewer.color_surface.reset_view()
	viewer.color_surface._update_crop()
	viewer.yaw = 0.0
	viewer.pitch = 0.0
	viewer.zoom = viewer.INITIAL_ZOOM
	viewer._apply_camera()
	viewer.hud.show()
	viewer.hud.insets_enabled = true
	viewer.hud.subject_lock = ""
	viewer.ports.show()
	viewer.hud.set_palette_label(viewer._palette_name())

func publish(status: String) -> void:
	var actual_look: String = "rgb.fixed.v1" if viewer.palette == 0 else "rgb.crimson.v1"
	if not viewer.color_mode:
		actual_look = "xyz.depth.v1" if viewer.palette == 2 else "xyz.crimson.v1"
	var receipt := {"schema_version": "furbomek.effects-ack.v1", "consumer_id": consumer_id,
		"status": status, "revision": revision, "owner": lease_owner, "cue_id": cue_id,
		"look": actual_look,
		"source_available": viewer.source_valid, "source_sequence": viewer.sequence,
		"framing": framing.reason, "matched_id": framing.matched_id,
		"depth_provenance": "native_measured_xyz_512x424" if not viewer.color_mode else "optical_rgb_no_extra_depth"}
	var path := directory.path_join("effects-ack.next")
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return
	file.store_string(JSON.stringify(receipt))
	file.close()
	DirAccess.rename_absolute(path, directory.path_join("effects-ack.json"))
