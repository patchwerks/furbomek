extends SceneTree

# Isolated real consumer with synthetic input; no camera, OBS or audio device.
const Source = preload("res://effect_fixture_source.gd")
var view: Node
var directory := ""
var until := 0
var refresh_at := 0
var frame: Dictionary

func _init() -> void:
	call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 1:
		quit(2)
		return
	directory = args[0]
	OS.set_environment("FURBOMEK_KINECT_DIR", directory)
	view = load("res://main.tscn").instantiate()
	root.add_child(view)
	view.set_process(false)
	frame = Source.snapshot()
	until = Time.get_ticks_msec() + 30000
	while Time.get_ticks_msec() < until:
		if FileAccess.file_exists(directory.path_join("fixture-exit")): break
		if FileAccess.file_exists(directory.path_join("fixture-manual")):
			view.effects.manual_override()
			DirAccess.remove_absolute(directory.path_join("fixture-manual"))
		if Time.get_ticks_msec() >= refresh_at:
			frame.produced_unix_ms = int(Time.get_unix_time_from_system() * 1000)
			view._apply_snapshot(frame)
			view.effects.update_snapshot(frame)
			refresh_at = Time.get_ticks_msec() + 100
		view.effects.tick()
		await process_frame
	print(JSON.stringify({"scope": "synthetic private mailbox", "revision": view.effects.revision, "owner": view.effects.lease_owner}))
	quit(0)
