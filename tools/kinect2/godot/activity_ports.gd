extends Control

const ActivityEventReader = preload("res://activity_event_reader.gd")
const POLL_MSEC := 125
const PANEL := Color(0.075, 0.008, 0.02, 0.9)
const CRIMSON := Color("a5232e")
const HOT := Color("ec3e49")
const INK := Color("c69a9a")
const MUTED := Color("895158")
const AMBER := Color("ff9b42")
const OFFLINE := Color("7e2630")
const SCREEN_TINT := Color(0.90, 0.63, 0.68)

var stream_directory := ""
var last_poll := 0
var reader = ActivityEventReader.new()
var activity: Dictionary = {}
var live := false
var sequence := -1
var valid_points := 0
var capture_fps := 0.0
var preview: ImageTexture
var screen_texture: ImageTexture
var screen_sequence := -1
var screen_was_stale := false


func configure(directory: String) -> void:
	stream_directory = directory
	reader.configure(directory)


func set_context(next_live: bool, next_sequence: int, points: int, fps: float) -> void:
	live = next_live
	sequence = next_sequence
	valid_points = points
	capture_fps = fps
	queue_redraw()


func tick() -> void:
	var now := Time.get_ticks_msec()
	_refresh_freshness()
	if now - last_poll < POLL_MSEC:
		return
	last_poll = now
	var result := reader.poll()
	if not result.get("changed", false):
		return
	_apply_activity(result.get("activity", {}))


func _refresh_freshness() -> void:
	if activity.is_empty():
		return
	var now := int(Time.get_unix_time_from_system() * 1000.0)
	if now > int(activity.get("expires_at_ms", 0)):
		_clear_activity()
		return
	var next_stale := _screen_is_stale(now)
	if next_stale != screen_was_stale:
		screen_was_stale = next_stale
		if next_stale:
			screen_texture = null
		queue_redraw()


func _apply_activity(next_activity: Dictionary) -> void:
	if next_activity.is_empty():
		_clear_activity()
		return
	var next_screen_value = next_activity.get("screen")
	if next_screen_value is Dictionary:
		var next_screen: Dictionary = next_screen_value
		if next_screen["state"] == "live":
			if _screen_data_is_stale(next_screen, int(Time.get_unix_time_from_system() * 1000.0)):
				screen_texture = null
			else:
				var texture = next_activity.get("_screen_texture")
				if not texture is ImageTexture:
					_clear_activity()
					return
				screen_texture = texture
			screen_sequence = int(next_screen["seq"])
		else:
			_clear_screen()
	else:
		_clear_screen()
	activity = next_activity
	preview = activity.get("_preview")
	screen_was_stale = _screen_is_stale(int(Time.get_unix_time_from_system() * 1000.0))
	queue_redraw()


func _clear_activity() -> void:
	activity = {}
	preview = null
	_clear_screen()
	queue_redraw()


func _clear_screen() -> void:
	screen_texture = null
	screen_sequence = -1
	screen_was_stale = false


func _screen_is_stale(now: int) -> bool:
	var value = activity.get("screen")
	if not value is Dictionary or value.get("state", "") != "live":
		return false
	return _screen_data_is_stale(value, now)


func _screen_data_is_stale(screen: Dictionary, now: int) -> bool:
	var age := now - int(screen.get("captured_at_ms", 0))
	return age < 0 or age > 2000


func _draw() -> void:
	var scale := minf(size.x / 1920.0, size.y / 1080.0)
	var origin := (size - Vector2(1920, 1080) * scale) * 0.5
	draw_set_transform(origin, 0.0, Vector2(scale, scale))
	_draw_screen_port()
	_draw_now_port()
	_draw_timeline_port()
	_draw_context_port()
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


func _draw_screen_port() -> void:
	var panel := Rect2(36, 122, 440, 294)
	var screen_rect := Rect2(46, 162, 420, 236)
	var screen_status := _screen_label()
	var color := _screen_color()
	_draw_port(panel, "HERMES / LIVE SCREEN", screen_status, color)
	if _screen_is_live():
		draw_texture_rect(screen_texture, screen_rect, false, SCREEN_TINT)
	elif not activity.is_empty() and not activity.has("screen") and preview != null:
		draw_texture_rect(preview, screen_rect, false, Color(0.45, 0.30, 0.33))
		_center_text(screen_rect, "PUBLIC PREVIEW / V1", 10, INK)
	else:
		draw_rect(screen_rect, Color("160409"))
		_center_text(screen_rect, screen_status, 13, color)
	draw_rect(Rect2(46, 402, 86, 4), color)
	_text(Vector2(146, 407), "SEQ %06d" % max(screen_sequence, 0), 9, MUTED)


func _draw_now_port() -> void:
	var panel := Rect2(36, 436, 440, 102)
	_draw_port(panel, "NOW", "PUBLIC ACTIVITY", _status_color())
	if activity.is_empty():
		_text(Vector2(52, 485), "IDLE", 13, MUTED)
		_text(Vector2(52, 510), "AWAITING PUBLIC ACTIVITY", 10, MUTED)
		return
	var status := str(activity["status"]).to_upper()
	var chip := Rect2(52, 467, 152, 17)
	draw_rect(chip, Color(_status_color(), 0.24))
	draw_line(chip.position, Vector2(chip.end.x, chip.position.y), _status_color(), 1.0)
	_text(Vector2(58, 480), _clip(status, 22), 10, _status_color())
	_text(Vector2(222, 480), "TOOL / %s" % _clip(str(activity["tool"]).to_upper(), 20), 10, INK)
	_text(Vector2(52, 504), _clip(str(activity["title"]).to_upper(), 52), 12, INK)
	_text(Vector2(52, 524), _clip(str(activity["summary"]), 60), 11, MUTED)


func _draw_timeline_port() -> void:
	var panel := Rect2(36, 558, 440, 310)
	_draw_port(panel, "ACTIVITY", "%d / 6" % _timeline().size(), HOT)
	var row_y := 606.0
	for item in _timeline():
		var color := HOT if item["status"] == "running" else OFFLINE if item["status"] == "error" else INK
		_text(Vector2(52, row_y), _age_label(int(item["age_s"])), 11, color)
		_text(Vector2(88, row_y), _clip(str(item["category"]).to_upper(), 11), 11, color)
		_text(Vector2(174, row_y), _clip(str(item["action"]).to_upper(), 30), 11, color)
		_text(Vector2(88, row_y + 16), _clip(str(item["detail"]), 48), 10, MUTED if item["status"] != "error" else OFFLINE)
		draw_line(Vector2(52, row_y + 24), Vector2(460, row_y + 24), Color(CRIMSON, 0.16), 1.0)
		row_y += 39.0


func _draw_context_port() -> void:
	var panel := Rect2(36, 900, 440, 132)
	_draw_port(panel, "CAMERA CONTEXT", "SENSOR LINK", INK if live else OFFLINE)
	_text(Vector2(52, 956), "STATE  %s" % ("LIVE" if live else "OFFLINE"), 12, INK if live else OFFLINE)
	_text(Vector2(52, 979), "SEQ    %06d" % max(sequence, 0), 10, MUTED)
	_text(Vector2(52, 1000), "DEPTH %06d / %.1f FPS" % [valid_points, capture_fps], 10, MUTED)


func _draw_port(rect: Rect2, title: String, status: String, color: Color) -> void:
	draw_rect(rect, PANEL)
	draw_rect(Rect2(rect.position, Vector2(rect.size.x, 31)), Color("26070c"))
	var corners := PackedVector2Array([rect.position, Vector2(rect.end.x - 18, rect.position.y), Vector2(rect.end.x, rect.position.y + 18), rect.end, Vector2(rect.position.x, rect.end.y)])
	draw_polyline(corners, CRIMSON, 2.0)
	draw_line(Vector2(rect.position.x, rect.end.y), rect.position, CRIMSON, 2.0)
	_text(rect.position + Vector2(14, 21), title, 10, INK)
	draw_string(get_theme_default_font(), rect.position + Vector2(0, 21), status, HORIZONTAL_ALIGNMENT_RIGHT, int(rect.size.x - 14), 10, color)


func _screen_is_live() -> bool:
	var value = activity.get("screen")
	return value is Dictionary and value.get("state", "") == "live" and not _screen_is_stale(int(Time.get_unix_time_from_system() * 1000.0)) and screen_texture != null


func _screen_label() -> String:
	if activity.is_empty():
		return "NO ACTIVITY"
	var value = activity.get("screen")
	if not value is Dictionary:
		return "PUBLIC PREVIEW" if preview != null else "SCREEN OFFLINE"
	if value["state"] == "shuttered":
		return "PRIVACY SHUTTER"
	if value["state"] == "offline":
		return "SCREEN OFFLINE"
	return "SCREEN STALE" if _screen_is_stale(int(Time.get_unix_time_from_system() * 1000.0)) else "LIVE / 4 FPS"


func _screen_color() -> Color:
	var label := _screen_label()
	return HOT if label.begins_with("LIVE") else OFFLINE if label == "PRIVACY SHUTTER" or label == "SCREEN STALE" else MUTED


func _status_color() -> Color:
	if activity.is_empty():
		return MUTED
	match str(activity["status"]).to_upper():
		"ACTING": return HOT
		"THINKING", "AWAITING APPROVAL": return AMBER
		"PRIVACY SHUTTER", "ERROR": return OFFLINE
		"IDLE": return MUTED
	return INK


func _timeline() -> Array:
	var value = activity.get("timeline", [])
	return value if value is Array else []


func _age_label(seconds: int) -> String:
	if seconds < 60:
		return "%ds" % seconds
	if seconds < 3600:
		return "%dm" % int(seconds / 60)
	return "%dh" % int(seconds / 3600)


func _clip(value: String, limit: int) -> String:
	return value.left(limit - 2) + ".." if value.length() > limit else value


func _center_text(rect: Rect2, value: String, font_size: int, color: Color) -> void:
	draw_string(get_theme_default_font(), Vector2(rect.position.x, rect.get_center().y + font_size * 0.35), value, HORIZONTAL_ALIGNMENT_CENTER, int(rect.size.x), font_size, color)


func _text(position: Vector2, value: String, font_size: int, color: Color) -> void:
	draw_string(get_theme_default_font(), position, value, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)
