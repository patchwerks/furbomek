extends RefCounted

const ActivityEventContract = preload("res://activity_event_contract.gd")

const LIMIT := 65536
const PNG_LIMIT := 4194304
const JPEG_LIMIT := 2097152

var stream_directory := ""
var cached_json := ""
var active_activity: Dictionary = {}
var accepted_sequence := -1
var preview_name := ""
var preview: ImageTexture
var screen_sequence := -1
var screen_texture: ImageTexture
var screen_release_floor := -1
var contract = ActivityEventContract.new()


func configure(directory: String) -> void:
	stream_directory = directory


func poll() -> Dictionary:
	return poll_at(int(Time.get_unix_time_from_system() * 1000.0))


func poll_at(now_ms: int) -> Dictionary:
	var path := stream_directory.path_join("activity.json")
	if not FileAccess.file_exists(path):
		cached_json = ""
		return _clear_active_activity()
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null or file.get_length() > LIMIT:
		cached_json = ""
		return _clear_active_activity()
	var raw := file.get_as_text()
	if raw == cached_json:
		if not active_activity.is_empty() and now_ms > int(active_activity["expires_at_ms"]):
			return _clear_active_activity()
		_clear_stale_screen(now_ms)
		return {"changed": false}
	cached_json = raw
	var parsed := contract.parse_event(raw, now_ms)
	if parsed.is_empty() or int(parsed["seq"]) <= accepted_sequence:
		return _clear_active_activity()
	var prepared := _load_visuals(parsed, now_ms)
	if prepared.is_empty():
		return _clear_active_activity()
	accepted_sequence = int(prepared["seq"])
	active_activity = prepared
	return {"changed": true, "activity": prepared}


func _clear_active_activity() -> Dictionary:
	var changed := not active_activity.is_empty()
	_latch_screen_release_floor()
	active_activity = {}
	_clear_visual_caches()
	return {"changed": changed, "activity": {}}


func _load_visuals(activity: Dictionary, now_ms: int) -> Dictionary:
	_clear_preview_cache()
	if activity.has("image_filename"):
		var next_preview := _load_public_png(str(activity["image_filename"]))
		if next_preview == null:
			return {}
		activity["_preview"] = next_preview
	if not activity.has("screen"):
		_clear_screen_cache()
		return activity
	var screen: Dictionary = activity["screen"]
	match screen["state"]:
		"live":
			if not _screen_is_current(screen, now_ms):
				_expire_screen(int(screen["seq"]))
				return activity
			if int(screen["seq"]) <= screen_release_floor:
				return {}
			var texture := _load_live_screen(screen)
			if texture == null:
				return {}
			activity["_screen_texture"] = texture
		"shuttered", "offline":
			_expire_screen(int(screen["seq"]))
	return activity


func _load_public_png(name: String) -> ImageTexture:
	if not contract.is_safe_preview_name(name):
		return null
	if name == preview_name and preview != null:
		return preview
	var path := stream_directory.path_join(name)
	if not FileAccess.file_exists(path):
		return null
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null or file.get_length() > PNG_LIMIT or file.get_length() < 24:
		return null
	file.big_endian = true
	file.seek(16)
	var width := file.get_32()
	var height := file.get_32()
	if width <= 0 or height <= 0 or width > 1024 or height > 1024:
		return null
	file.seek(0)
	var image := Image.new()
	if image.load_png_from_buffer(file.get_buffer(file.get_length())) != OK:
		return null
	preview_name = name
	preview = ImageTexture.create_from_image(image)
	return preview


func _load_live_screen(screen: Dictionary) -> ImageTexture:
	if int(screen["seq"]) == screen_sequence and screen_texture != null:
		return screen_texture
	var path := stream_directory.path_join(str(screen["filename"]))
	if not FileAccess.file_exists(path):
		return null
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null or file.get_length() < 4 or file.get_length() > JPEG_LIMIT:
		return null
	var bytes := file.get_buffer(file.get_length())
	if bytes[0] != 0xFF or bytes[1] != 0xD8 or bytes[bytes.size() - 2] != 0xFF or bytes[bytes.size() - 1] != 0xD9:
		return null
	var image := Image.new()
	if image.load_jpg_from_buffer(bytes) != OK:
		return null
	if image.get_width() != int(screen["width"]) or image.get_height() != int(screen["height"]):
		return null
	screen_sequence = int(screen["seq"])
	screen_texture = ImageTexture.create_from_image(image)
	return screen_texture


func _clear_stale_screen(now_ms: int) -> void:
	if active_activity.has("screen"):
		var screen: Dictionary = active_activity["screen"]
		if screen["state"] == "live" and not _screen_is_current(screen, now_ms):
			_expire_screen(int(screen["seq"]))


func _expire_screen(sequence: int) -> void:
	screen_release_floor = max(screen_release_floor, sequence)
	_clear_screen_cache()


func _latch_screen_release_floor() -> void:
	var active_screen_sequence := -1
	if active_activity.has("screen"):
		active_screen_sequence = int(active_activity["screen"]["seq"])
	screen_release_floor = max(screen_release_floor, max(active_screen_sequence, screen_sequence))


func _clear_visual_caches() -> void:
	_clear_preview_cache()
	_clear_screen_cache()


func _clear_preview_cache() -> void:
	preview_name = ""
	preview = null


func _clear_screen_cache() -> void:
	screen_sequence = -1
	screen_texture = null


func _screen_is_current(screen: Dictionary, now_ms: int) -> bool:
	var age := now_ms - int(screen["captured_at_ms"])
	return age >= 0 and age <= 2000
