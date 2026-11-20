extends SceneTree

var view: Node
var frame: Dictionary
var control: Dictionary
var destination: String
var index := 0

func _init() -> void:
	call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2 or DisplayServer.get_name() == "headless":
		quit(2)
		return
	destination = args[1]
	OS.set_environment("FURBOMEK_KINECT_DIR", args[0])
	view = load("res://main.tscn").instantiate()
	root.add_child(view)
	view.set_process(false)
	root.title = "Furbomek offline effects fixture"
	root.content_scale_size = Vector2i(1920, 1080)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.size = Vector2i(1280, 720)
	# Read the archived sensor bytes through the real decoder; never synthesize XYZ.
	var archived: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0].path_join("tracking.json")))
	var sequence := int(archived.sequence)
	var geometry: Dictionary = view.loader._read_frame(args[0].path_join(archived.frame_file), sequence)
	var optical: Texture2D = view.loader._read_jpeg(args[0].path_join(archived.optical_file), sequence, Vector2i(1920,1080))
	var registered: Texture2D = view.loader._read_jpeg(args[0].path_join(archived.image_file), sequence, Vector2i(512,424))
	if geometry.is_empty() or optical == null or registered == null:
		printerr("Archived same-sequence decode failed")
		quit(1)
		return
	frame = archived.duplicate(true)
	frame.merge({"geometry":geometry.geometry,"count":geometry.count,"optical":optical,"registered":registered}, true)
	# Replay time is explicit; original sensor capture timestamp remains in the source manifest.
	frame.produced_unix_ms = int(Time.get_unix_time_from_system() * 1000)
	frame.capture_fps = 0.0
	view._apply_snapshot(frame)
	view.effects.update_snapshot(frame)
	var label := Label.new()
	label.text = "OFFLINE ARCHIVED SENSOR REPLAY / NO LIVE ACCURACY OR PERFORMANCE CLAIM"
	label.position = Vector2(550, 1035)
	label.z_index = 100
	label.add_theme_font_size_override("font_size", 18)
	view.get_node("Hud").add_child(label)
	control = JSON.parse_string(FileAccess.get_file_as_string("res://../effects/fixtures/control.json"))
	var records := FileAccess.open(destination.path_join("frames.jsonl"), FileAccess.WRITE)
	var movie_mode := "--write-movie" in OS.get_cmdline_args()
	for look in ["rgb.fixed.v1", "rgb.crimson.v1", "xyz.depth.v1", "xyz.crimson.v1", "pulse", "loss", "expired", "hidden_slots", "bounded_orbit"]:
		control.consumer_id = view.effects.consumer_id
		control.expected_revision = view.effects.revision
		control.revision = view.effects.revision + 1
		control.issued_ms = int(Time.get_unix_time_from_system() * 1000)
		control.look = look if look in ["rgb.fixed.v1", "rgb.crimson.v1", "xyz.depth.v1", "xyz.crimson.v1"] else "rgb.crimson.v1"
		control.insets_visible = look != "hidden_slots"
		if look == "bounded_orbit":
			control.look = "xyz.depth.v1"
			control.yaw = 0.3
			control.pitch = 0.1
			control.zoom = 1.3
			control.point_pixels = 2.0
		control.pulse_hz = 1.0 if look == "pulse" else 0.0
		control.intensity_percent = 100
		control.framing.rules = ["fixed"]
		var outcome: String = view.effects.accept(JSON.stringify(control))
		if outcome != "applied":
			printerr(outcome)
			quit(1)
			return
		if look == "loss":
			view._hide_stale()
		if look == "expired":
			view._apply_snapshot(frame)
			view.effects.expires_at = 0
		for step in 12:
			view.effects.tick()
			label.queue_redraw()
			await process_frame
			await RenderingServer.frame_post_draw
			await process_frame
			await RenderingServer.frame_post_draw
			var name := "frame-%04d.png" % index
			if not movie_mode:
				var pixels := root.get_texture().get_image()
				if pixels == null or pixels.get_size() != Vector2i(1920,1080) or pixels.save_png(destination.path_join(name)) != OK:
					quit(1)
					return
			records.store_line(JSON.stringify({"file":name,"case":look,"step":step,"movie_frame":Engine.get_frames_drawn() - 1,"elapsed_ms":Time.get_ticks_msec(),"source_sequence":sequence,"revision":view.effects.revision,"measured_points":frame.valid_points}))
			index += 1
		view._apply_snapshot(frame)
	records.close()
	print(JSON.stringify({"passed":true,"frames":index,"width":1920,"height":1080,"scope":"archived_sensor_fixture"}))
	view.queue_free()
	quit(0)
