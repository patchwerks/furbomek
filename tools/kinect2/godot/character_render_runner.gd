extends SceneTree

# Offline fixture host for the shipped Control. Never reads camera/device paths.
const ActivityPorts = preload("res://activity_ports.gd")
var view: Control
var destination := ""
var started := 0
var last_capture := -100
var frame_index := 0
var last_seq := -1
var records: FileAccess


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 3 or arguments[2] not in ["full", "focus"] or DisplayServer.get_name() == "headless":
		printerr("Expected public snapshot and capture directories, with a real renderer")
		quit(2)
		return
	destination = arguments[1]
	root.mode = Window.MODE_WINDOWED
	root.borderless = false
	root.size = Vector2i(1280, 720)
	root.content_scale_size = Vector2i(1920, 1080)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.title = "Furbomek offline character fixture"
	RenderingServer.set_default_clear_color(Color("050204"))
	view = ActivityPorts.new()
	if arguments[2] == "focus":
		var crop := Control.new()
		crop.position = Vector2(240, 330)
		crop.size = Vector2(1440, 372)
		crop.clip_contents = true
		root.add_child(crop)
		crop.add_child(view)
		view.scale = Vector2(3, 3)
		view.position = Vector2(-48, -1278)
		var title := Label.new()
		title.text = "FURBOMEK / OFFLINE CHARACTER TEST"
		title.position = Vector2(240, 210)
		title.add_theme_font_size_override("font_size", 36)
		title.add_theme_color_override("font_color", Color("c69a9a"))
		root.add_child(title)
		var subtitle := Label.new()
		subtitle.text = "Actual display. Synthetic events."
		subtitle.position = Vector2(240, 265)
		subtitle.add_theme_font_size_override("font_size", 26)
		subtitle.add_theme_color_override("font_color", Color("895158"))
		root.add_child(subtitle)
	else:
		root.add_child(view)
	view.size = Vector2(1920, 1080)
	view.configure(arguments[0])
	records = FileAccess.open(destination.path_join("frames.jsonl"), FileAccess.WRITE)
	if records == null:
		quit(2)
		return
	await process_frame
	await RenderingServer.frame_post_draw
	var ready := FileAccess.open(destination.path_join("ready"), FileAccess.WRITE)
	ready.store_string("ready")
	ready.close()
	started = Time.get_ticks_msec()
	while Time.get_ticks_msec() - started < 35000:
		view.tick()
		await RenderingServer.frame_post_draw
		var elapsed := Time.get_ticks_msec() - started
		var sequence := int(view.activity.get("seq", -1))
		if elapsed - last_capture >= 100 or sequence != last_seq:
			var pixels := root.get_texture().get_image()
			var captured_ms := int(Time.get_unix_time_from_system() * 1000.0)
			if pixels == null or pixels.is_empty():
				printerr("Renderer returned no pixels")
				quit(1)
				return
			var filename := "frame-%05d.png" % frame_index
			if pixels.save_png(destination.path_join(filename)) != OK:
				quit(1)
				return
			records.store_line(JSON.stringify({"frame": filename, "captured_ms": captured_ms,
				"elapsed_ms": elapsed, "status": view.activity.get("status", ""),
				"publication_seq": sequence, "width": pixels.get_width(), "height": pixels.get_height()}))
			records.flush()
			frame_index += 1
			last_capture = elapsed
			last_seq = sequence
		if FileAccess.file_exists(destination.path_join("finish")):
			break
		await process_frame
	records.close()
	view.queue_free()
	quit(0)
