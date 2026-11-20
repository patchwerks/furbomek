extends SceneTree

const Request = preload("res://effect_request.gd")
const Source = preload("res://effect_fixture_source.gd")
var failures: Array[String] = []
var assertions := 0
var view: Node
var folder := ""
var control: Dictionary

func _init() -> void:
	call_deferred("run")

func check(value: bool, label: String) -> void:
	assertions += 1
	print(("PASS " if value else "FAIL ") + label)
	if not value:
		failures.append(label)

func request() -> Dictionary:
	var result := control.duplicate(true)
	result.consumer_id = view.effects.consumer_id
	result.expected_revision = view.effects.revision
	result.revision = view.effects.revision + 1
	result.issued_ms = int(Time.get_unix_time_from_system() * 1000)
	return result

func run() -> void:
	var temporary := DirAccess.create_temp("furbomek-effects-", false)
	folder = temporary.get_current_dir()
	OS.set_environment("FURBOMEK_KINECT_DIR", folder)
	view = load("res://main.tscn").instantiate()
	root.add_child(view)
	view.set_process(false)
	control = JSON.parse_string(FileAccess.get_file_as_string("res://../effects/fixtures/control.json"))
	var frame := Source.snapshot()
	view._apply_snapshot(frame)
	view.effects.update_snapshot(frame)
	var catalog: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../effects/catalog.json"))
	for definition in catalog.looks:
		var look: String = definition.id
		var cue := request()
		cue.look = look
		var result: String = view.effects.accept(JSON.stringify(cue))
		check(result == "applied" and view.effects.revision == cue.revision, "revision ACK " + look)
		check(view.mesh.buffer == frame.geometry, "native holes unchanged " + look)
		check(view.color_mode == look.begins_with("rgb"), "actual surface " + look)
	var cue := request()
	cue.look = "rgb.crimson.v1"
	check(view.effects.accept(JSON.stringify(cue)) == "applied", "crimson apply")
	check(view.effects.accept(JSON.stringify(cue)) == "conflict", "late duplicate revision rejected")
	for mutation in [{"consumer_id":"previous-process"}, {"expected_revision":0}, {"revision":999}, {"issued_ms":1}, {"look":"ir.native.v1"}, {"shader":"evil"}, {"pulse_hz":1.1}, {"duration_ms":30001}, {"zoom":"1.2"}, {"hud_visible":1}, {"intensity_percent":1.2}, {"point_pixels":-1}, {"owner":"../../private"}]:
		var bad := request()
		bad.merge(mutation, true)
		var before: int = view.effects.revision
		check(view.effects.accept(JSON.stringify(bad)) != "applied" and view.effects.revision == before, "reject " + JSON.stringify(mutation))
	check(view.effects.accept("null") == "invalid", "reject null")
	check(view.effects.accept("{".repeat(8193)) == "invalid", "reject oversize")
	for bad_framing in [{"subject_id":"object-furbomek","rules":["subject","subject"],"ttl_ms":600}, {"subject_id":"object-furbomek","rules":["surface"],"ttl_ms":600}, {"subject_id":"object-furbomek","rules":["fixed"],"ttl_ms":601}, {"subject_id":"object-furbomek","rules":["fixed"],"ttl_ms":1.1}]:
		var bad := request()
		bad.framing = bad_framing
		check(view.effects.accept(JSON.stringify(bad)) == "invalid", "reject malformed framing " + JSON.stringify(bad_framing))
	var mailbox := request()
	mailbox.look = "xyz.crimson.v1"
	mailbox.insets_visible = false
	var file := FileAccess.open(folder.path_join("effects.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(mailbox))
	file.close()
	view.effects.poll_at = 0
	view.effects.tick()
	var ack: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("effects-ack.json")))
	check(ack.status == "applied" and ack.revision == mailbox.revision and ack.consumer_id == mailbox.consumer_id and ack.owner == mailbox.owner, "actual mailbox atomic ACK identity and revision")
	check(not view.hud.insets_enabled and not view.hud.processed.visible and not view.hud.optical.visible, "inset visibility gates slot and image")
	var parameters := request()
	parameters.look = "xyz.depth.v1"
	parameters.point_pixels = 3.6
	parameters.zoom = 1.5
	parameters.yaw = -0.55
	parameters.pitch = 0.32
	parameters.hud_visible = false
	view.effects.accept(JSON.stringify(parameters))
	check(is_equal_approx(view.camera.position.z, view.INITIAL_ZOOM / 1.5) and is_equal_approx(view.orbit.rotation.y, -0.55) and is_equal_approx(view.orbit.rotation.x, 0.32), "bounded zoom and orbit applied to actual camera")
	check(is_equal_approx(view.material.get_shader_parameter("point_pixels"), 3.6), "point parameter applied to actual shader")
	check(not view.hud.visible and not view.ports.visible, "HUD and slots hidden together")
	var selected := request()
	selected.framing.rules = ["subject", "hold"]
	view.effects.accept(JSON.stringify(selected))
	frame.tracks = [{"id":"object-furbomek","kind":"object","optical_box":[0.2,0.2,0.2,0.3]}]
	view.effects.update_snapshot(frame)
	var crop: Rect2 = view.color_surface.crop
	check(view.effects.framing.matched_id == "object-furbomek" and crop.size.x < 1, "exact subject acquired")
	check(view.hud.subject_lock == "object-furbomek", "HUD shares requested subject identity")
	frame.tracks = [{"id":"unrelated","kind":"surface","optical_box":[0.7,0.1,0.1,0.1]}]
	view.effects.update_snapshot(frame)
	check(view.color_surface.crop == crop and view.effects.framing.matched_id == "", "loss holds crop without surface impersonation")
	frame.produced_unix_ms -= 1000
	frame.tracks = [{"id":"object-furbomek","kind":"object","optical_box":[0.7,0.1,0.1,0.1]}]
	view.effects.update_snapshot(frame)
	check(view.color_surface.crop == crop and view.effects.framing.matched_id == "", "stale subject cannot pan")
	check(view.hud.selected.is_empty(), "stale lock clears HUD identity")
	var fixed := request()
	fixed.framing.rules = ["fixed", "subject"]
	view.effects.accept(JSON.stringify(fixed))
	check(view.color_surface.crop == Rect2(0,0,1,1), "rule order fixed before subject")
	var key := InputEventKey.new()
	key.keycode = KEY_3
	key.pressed = true
	view._unhandled_input(key)
	ack = JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("effects-ack.json")))
	check(ack.look == "xyz.depth.v1" and ack.owner == "operator", "operator ACK reflects actual native view")
	view.effects.expires_at = 0
	view.effects.tick()
	check(not view.color_mode and view.effects.effective == null, "expired old lease preserves manual edit")
	frame.produced_unix_ms = int(Time.get_unix_time_from_system() * 1000)
	frame.tracks = [{"id":"object-furbomek","kind":"object","optical_box":[0.2,0.2,0.2,0.3]}]
	view._apply_snapshot(frame)
	view.effects.update_snapshot(frame)
	view.effects.accept(JSON.stringify(request()))
	check(view.effects.framing.crop.size.x < 1, "non-full subject cache immediately before expiry")
	view.effects.expires_at = 0
	view.effects.tick()
	check(view.color_mode and view.palette == 0 and not view.effects.pulse.visible, "expiry restores fixed RGB without pulse")
	var hold := request()
	hold.framing.rules = ["hold"]
	view.effects.accept(JSON.stringify(hold))
	check(view.color_surface.crop == Rect2(0,0,1,1), "new hold after expiry cannot restore obsolete subject crop")
	view.effects.accept(JSON.stringify(request()))
	var wheel := InputEventMouseButton.new()
	wheel.button_index = MOUSE_BUTTON_WHEEL_UP
	wheel.pressed = true
	view._unhandled_input(wheel)
	var manual_crop: Rect2 = view.color_surface.get_meta("view_crop")
	check(manual_crop.size.x < 1, "manual wheel created bounded crop")
	hold = request()
	hold.framing.rules = ["hold"]
	hold.zoom = 1.0
	view.effects.accept(JSON.stringify(hold))
	check(view.color_surface.get_meta("view_crop") == manual_crop, "new hold preserves actual manual zoom crop")
	var bounded := request()
	bounded.actor_id = "fixture-actor"
	bounded.expected_owner = view.effects.lease_owner
	bounded.operation = "apply"
	bounded.framing = {"subject_id":"object-furbomek", "rules":["fixed"], "ttl_ms":300,
		"roi":{"x":0.5,"y":0.2,"width":0.3,"height":0.4},
		"transition":{"duration_ms":500,"pan_units_per_second":0.1,"zoom":1.0,"zoom_per_second":0.2}}
	check(view.effects.accept(JSON.stringify(bounded)) == "applied", "trusted bounded ROI accepted by real consumer")
	var transition = load("res://effect_framing.gd").new()
	var parsed = Request.parse(JSON.stringify(bounded))
	var first: Rect2 = transition.advance(parsed, frame, int(Time.get_unix_time_from_system() * 1000), 1000)
	var second: Rect2 = transition.advance(parsed, frame, int(Time.get_unix_time_from_system() * 1000), 2000)
	check(first == Rect2(0,0,1,1) and second != first, "transition begins at actual previous crop")
	check(first.get_center().distance_to(second.get_center()) <= 0.100001, "pan speed upper bound")
	check(first.size.distance_to(second.size) <= 0.200001, "zoom speed upper bound")
	for tick in range(3000, 12000, 1000):
		transition.advance(parsed, frame, int(Time.get_unix_time_from_system() * 1000), tick)
	check(transition.crop.is_equal_approx(Rect2(0.5,0.2,0.3,0.4)), "bounded fixed ROI reached")
	parsed.rules.assign(["hold"])
	var held: Rect2 = transition.crop
	check(transition.advance(parsed, frame, int(Time.get_unix_time_from_system() * 1000), 13000) == held, "owner hold preserves actual transitioned crop")
	parsed.valid_until_ms = 10
	parsed.fallback_roi = Rect2(0.1,0.1,0.8,0.8)
	for tick in range(14000, 24000, 1000):
		transition.advance(parsed, frame, 11, tick)
	check(transition.crop.is_equal_approx(parsed.fallback_roi), "expired trusted selection uses stable fixed fallback")
	parsed.valid_until_ms = 0
	parsed.look = "rgb.fixed.v1"
	check(transition.advance(parsed, frame, int(Time.get_unix_time_from_system() * 1000), 14000) == Rect2(0,0,1,1), "direct fixed RGB remains independent of advanced ROI")
	for malformed in [{}, {"duration_ms":"bad"}, {"duration_ms":500.5,"pan_units_per_second":0.1,"zoom":1,"zoom_per_second":0.2}, []]:
		var nested := request()
		nested.framing.transition = malformed
		check(Request.parse(JSON.stringify(nested)) == null, "malformed transition rejected " + JSON.stringify(malformed))
	var owner_bad := request()
	owner_bad.expected_owner = "stale-owner"
	check(view.effects.accept(JSON.stringify(owner_bad)) == "owner_conflict", "actual owner CAS refuses stale owner")
	bounded.framing.roi.x = 0.9
	check(Request.parse(JSON.stringify(bounded)) == null, "ROI beyond optical bounds rejected")
	bounded.framing.roi.x = 0.5
	bounded.framing.transition.pan_units_per_second = 2
	check(Request.parse(JSON.stringify(bounded)) == null, "unsafe transition rate rejected")
	view._hide_stale()
	check(view.effects.accept(JSON.stringify(request())) == "source_unavailable", "source loss cannot acquire effect")
	check(not view.cloud.visible and not view.color_surface.visible, "stale geometry and optical hidden")
	print(JSON.stringify({"passed":failures.is_empty(),"assertions":assertions,"failures":failures}))
	view.queue_free()
	await process_frame
	for name in DirAccess.get_files_at(folder):
		DirAccess.remove_absolute(folder.path_join(name))
	DirAccess.remove_absolute(folder)
	quit(0 if failures.is_empty() else 1)
