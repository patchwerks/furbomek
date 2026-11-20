extends SceneTree

const Loader = preload("res://stream_loader.gd")
var loader = Loader.new()
var directory := ""
var ready_count := 0
var expired_count := 0
var failures: Array[String] = []

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var temporary := DirAccess.create_temp("furbomek-stream-fixture-", false)
	if temporary == null:
		printerr("Cannot create fixture directory")
		quit(1)
		return
	directory = temporary.get_current_dir()
	root.add_child(loader)
	loader.configure(directory)
	loader.snapshot_ready.connect(func(_snapshot: Dictionary): ready_count += 1)
	loader.snapshot_expired.connect(func(): expired_count += 1)
	_write_cloud(1)
	_write_jpeg("frame-1.jpg.bin", 1, Vector2i(512, 424))
	_write_jpeg("frame-1.optical.bin", 1, Vector2i(1920, 1080))
	_write_tracking(1, 700)
	await create_timer(0.05).timeout
	loader.tick()
	_expect(ready_count == 0, "stale camera snapshot refused")
	_write_jpeg("frame-1.optical.bin", 2, Vector2i(1920, 1080))
	_write_tracking(1, 0)
	await create_timer(0.05).timeout
	loader.tick()
	_expect(ready_count == 0, "mixed optical sequence refused")
	_write_jpeg("frame-1.optical.bin", 1, Vector2i(1920, 1080))
	_write_tracking(1, 0)
	await create_timer(0.05).timeout
	loader.tick()
	_expect(ready_count == 1 and loader.live, "same-sequence snapshot accepted")
	await create_timer(0.65).timeout
	loader.tick()
	_expect(expired_count == 1 and not loader.live, "expired camera snapshot cleared")
	_write_cloud(2)
	_write_jpeg("frame-1.jpg.bin", 2, Vector2i(512, 424))
	_write_jpeg("frame-1.optical.bin", 2, Vector2i(1920, 1080))
	_write_tracking(2, 0)
	await create_timer(0.05).timeout
	loader.tick()
	_expect(ready_count == 2 and loader.live, "fresh camera snapshot recovered")
	for name in DirAccess.get_files_at(directory):
		DirAccess.remove_absolute(directory.path_join(name))
	DirAccess.remove_absolute(directory)
	print(JSON.stringify({"passed": failures.is_empty(), "ready_count": ready_count, "expired_count": expired_count, "failures": failures}))
	quit(0 if failures.is_empty() else 1)

func _expect(value: bool, scenario: String) -> void:
	if not value:
		failures.append(scenario)
	print(("PASS " if value else "FAIL ") + scenario)

func _write_cloud(sequence: int) -> void:
	var file := FileAccess.open(directory.path_join("frame-1.bin"), FileAccess.WRITE)
	for value in [0x32434B46, 1, sequence, 217088]:
		file.store_32(value)
	var points := PackedByteArray()
	points.resize(217088 * 64)
	file.store_buffer(points)

func _write_jpeg(name: String, sequence: int, size: Vector2i) -> void:
	var image := Image.create(size.x, size.y, false, Image.FORMAT_RGB8)
	image.fill(Color(0.1, 0.2, 0.3))
	var file := FileAccess.open(directory.path_join(name), FileAccess.WRITE)
	file.store_32(sequence)
	file.store_buffer(image.save_jpg_to_buffer())

func _write_tracking(sequence: int, age_ms: int) -> void:
	var file := FileAccess.open(directory.path_join("tracking.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify({
		"schema": "furbomek.vision.v1", "sequence": sequence,
		"produced_unix_ms": int(Time.get_unix_time_from_system() * 1000) - age_ms,
		"ttl_ms": 600, "frame_file": "frame-1.bin",
		"image_file": "frame-1.jpg.bin", "optical_file": "frame-1.optical.bin",
		"tracks": [], "valid_points": 0, "capture_fps": 15.0
	}))
