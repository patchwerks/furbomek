extends Control

const LIMIT := 65536
const POLL_MSEC := 300
const PANEL := Color(0.075, 0.008, 0.02, 0.9)
const CRIMSON := Color("a5232e")
const INK := Color("c69a9a")
const MUTED := Color("895158")

var stream_directory := ""
var last_poll := 0
var activity: Dictionary = {}
var live := false
var sequence := -1
var valid_points := 0
var capture_fps := 0.0
var preview: ImageTexture


func configure(directory: String) -> void:
	stream_directory = directory


func set_context(next_live: bool, next_sequence: int, points: int, fps: float) -> void:
	live = next_live
	sequence = next_sequence
	valid_points = points
	capture_fps = fps
	queue_redraw()


func tick() -> void:
	var now := Time.get_ticks_msec()
	if now - last_poll < POLL_MSEC:
		return
	last_poll = now
	activity = _read_activity()
	preview = activity.get("_preview")
	queue_redraw()


func _read_activity() -> Dictionary:
	var path := stream_directory.path_join("activity.json")
	if not FileAccess.file_exists(path):
		return {}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null or file.get_length() > LIMIT:
		return {}
	var value = JSON.parse_string(file.get_as_text())
	if not value is Dictionary:
		return {}
	var event: Dictionary = value
	if event.get("schemaVersion", "") != "furbomek.character.v1" or event.get("kind", "") != "agent.activity":
		return {}
	if not ["hermes-adapter", "a2ui-adapter", "glimpse-adapter"].has(event.get("source", "")):
		return {}
	if event.get("audience", "") != "public" or event.get("sensitivity", "") != "public":
		return {}
	var ttl := int(event.get("ttlMs", 0))
	var observed := str(event.get("observedAt", ""))
	if observed.length() < 20 or observed.length() > 32 or not observed.contains("T") or not observed.ends_with("Z"):
		return {}
	var produced := int(Time.get_unix_time_from_datetime_string(observed.get_slice(".", 0).trim_suffix("Z")) * 1000)
	if observed.contains("."):
		var fraction := observed.get_slice(".", 1).trim_suffix("Z")
		if not fraction.is_valid_int():
			return {}
		produced += int(fraction.left(3).rpad(3, "0"))
	var now := int(Time.get_unix_time_from_system() * 1000.0)
	if int(event.get("seq", -1)) < 0 or ttl <= 0 or ttl > 30000 or produced <= 0 or now - produced < 0 or now - produced > ttl:
		return {}
	var value_payload = event.get("payload", {})
	if not value_payload is Dictionary:
		return {}
	var payload: Dictionary = value_payload
	var result: Dictionary = {}
	for key in ["title", "summary", "status", "tool"]:
		if not payload.has(key) or not payload[key] is String or str(payload[key]).length() > 180:
			return {}
		result[key] = payload[key]
	if payload.has("image_filename"):
		var texture := _load_public_png(str(payload["image_filename"]))
		if texture == null:
			return {}
		result["_preview"] = texture
	return result


func _load_public_png(name: String) -> ImageTexture:
	if not name.ends_with(".png") or name.contains("/") or name.contains("\\") or name.length() > 96:
		return null
	if not name.get_basename().is_valid_filename():
		return null
	var path := stream_directory.path_join(name)
	if not FileAccess.file_exists(path):
		return null
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null or file.get_length() > 4194304:
		return null
	if file.get_length() < 24:
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
	return ImageTexture.create_from_image(image)


func _draw() -> void:
	var scale := minf(size.x / 1920.0, size.y / 1080.0)
	var origin := (size - Vector2(1920, 1080) * scale) * 0.5
	draw_set_transform(origin, 0.0, Vector2(scale, scale))
	_draw_port(Rect2(54, 150, 258, 284 if preview != null else 122), "HERMES / PUBLIC ACTIVITY")
	if activity.is_empty():
		_text(Vector2(69, 206), "IDLE", 14, INK)
		_text(Vector2(69, 228), "AWAITING PUBLIC ACTIVITY", 10, MUTED)
	else:
		_text(Vector2(69, 198), str(activity["title"]).to_upper().left(30), 12, INK)
		_text(Vector2(69, 218), str(activity["status"]).to_upper().left(30), 10, Color("ff9b42"))
		_text(Vector2(69, 242), str(activity["summary"]).left(34), 10, MUTED)
		if preview != null:
			draw_texture_rect(preview, Rect2(62, 280, 242, 144), false, Color(0.45, 0.30, 0.33))
	_draw_port(Rect2(54, 740, 258, 132), "CAMERA CONTEXT")
	_text(Vector2(69, 796), "STATE  %s" % ("LIVE" if live else "OFFLINE"), 12, INK if live else Color("7e2630"))
	_text(Vector2(69, 819), "SEQ    %06d" % max(sequence, 0), 10, MUTED)
	_text(Vector2(69, 840), "DEPTH %06d / %.1f FPS" % [valid_points, capture_fps], 10, MUTED)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


func _draw_port(rect: Rect2, title: String) -> void:
	draw_rect(rect, PANEL)
	draw_line(rect.position, Vector2(rect.end.x - 16, rect.position.y), CRIMSON, 2.0)
	draw_line(Vector2(rect.end.x - 16, rect.position.y), Vector2(rect.end.x, rect.position.y + 16), CRIMSON, 2.0)
	draw_line(Vector2(rect.end.x, rect.position.y + 16), rect.end, CRIMSON, 2.0)
	draw_line(rect.end, Vector2(rect.position.x, rect.end.y), CRIMSON, 2.0)
	draw_line(Vector2(rect.position.x, rect.end.y), rect.position, CRIMSON, 2.0)
	_text(rect.position + Vector2(14, 23), title, 10, INK)


func _text(position: Vector2, value: String, font_size: int, color: Color) -> void:
	draw_string(get_theme_default_font(), position, value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)
