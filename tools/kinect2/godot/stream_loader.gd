extends Node

signal snapshot_ready(snapshot: Dictionary)
signal snapshot_expired

const MAGIC := 0x32434B46
const HEADER_BYTES := 16
const POINT_COUNT := 217088
const FLOATS_PER_POINT := 16
const JSON_LIMIT := 65536
const JPEG_LIMIT := 16777216
const POLL_MSEC := 33

var stream_directory := "/dev/shm/furbomek-kinect2-1000"
var last_poll := 0
var last_sequence := -1
var live := false
var active_snapshot: Dictionary = {}


func configure(directory: String) -> void:
	if not directory.is_empty():
		stream_directory = directory


func tick() -> void:
	var now := Time.get_ticks_msec()
	if now - last_poll >= POLL_MSEC:
		last_poll = now
		_try_load()
	_update_freshness()


func _try_load() -> void:
	var tracking := _read_json(stream_directory.path_join("tracking.json"))
	if tracking.is_empty() or tracking.get("schema", "") != "furbomek.vision.v1":
		return
	var sequence := int(tracking.get("sequence", -1))
	if sequence < 0 or not _is_fresh(tracking):
		return
	if sequence == last_sequence:
		live = true
		return
	var frame_name := str(tracking.get("frame_file", ""))
	var image_name := str(tracking.get("image_file", ""))
	var optical_name := str(tracking.get("optical_file", ""))
	if not _safe_name(frame_name, ".bin") or not _safe_name(image_name, ".jpg.bin") or not _safe_name(optical_name, ".optical.bin"):
		return
	var frame := _read_frame(stream_directory.path_join(frame_name), sequence)
	var registered := _read_jpeg(stream_directory.path_join(image_name), sequence, Vector2i(512, 424))
	var optical := _read_jpeg(stream_directory.path_join(optical_name), sequence, Vector2i(1920, 1080))
	if frame.is_empty() or registered == null or optical == null:
		return
	if int(frame["sequence"]) != sequence:
		return
	active_snapshot = {
		"sequence": sequence,
		"geometry": frame["geometry"],
		"count": frame["count"],
		"registered": registered,
		"optical": optical,
		"tracks": tracking.get("tracks", []),
		"valid_points": int(tracking.get("valid_points", 0)),
		"capture_fps": float(tracking.get("capture_fps", 0.0)),
		"produced_unix_ms": int(tracking.get("produced_unix_ms", 0)),
		"ttl_ms": int(tracking.get("ttl_ms", 0))
	}
	last_sequence = sequence
	live = true
	snapshot_ready.emit(active_snapshot)


func _update_freshness() -> void:
	var next_live := not active_snapshot.is_empty() and _is_fresh(active_snapshot)
	if live and not next_live:
		live = false
		snapshot_expired.emit()


func _is_fresh(record: Dictionary) -> bool:
	var ttl := int(record.get("ttl_ms", 0))
	var produced := int(record.get("produced_unix_ms", 0))
	var now := int(Time.get_unix_time_from_system() * 1000.0)
	return ttl > 0 and ttl <= 5000 and produced > 0 and now - produced >= 0 and now - produced <= ttl


func _safe_name(name: String, suffix: String) -> bool:
	if not name.ends_with(suffix):
		return false
	for index in 4:
		var expected := "frame-%d%s" % [index, suffix]
		if name == expected:
			return true
	return false


func _read_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null or file.get_length() > JSON_LIMIT:
		return {}
	var value = JSON.parse_string(file.get_as_text())
	return value if value is Dictionary else {}


func _read_frame(path: String, expected_sequence: int) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var file := FileAccess.open(path, FileAccess.READ)
	var payload_bytes := POINT_COUNT * FLOATS_PER_POINT * 4
	if file == null or file.get_length() != HEADER_BYTES + payload_bytes:
		return {}
	file.big_endian = false
	var magic := file.get_32()
	var version := file.get_32()
	var sequence := file.get_32()
	var count := file.get_32()
	if magic != MAGIC or version != 1 or sequence != expected_sequence or count != POINT_COUNT:
		return {}
	var payload := file.get_buffer(payload_bytes)
	var geometry := payload.to_float32_array()
	if geometry.size() != POINT_COUNT * FLOATS_PER_POINT:
		return {}
	return {"sequence": sequence, "count": count, "geometry": geometry}


func _read_jpeg(path: String, expected_sequence: int, expected_size: Vector2i) -> ImageTexture:
	if not FileAccess.file_exists(path):
		return null
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null or file.get_length() < 8 or file.get_length() > JPEG_LIMIT:
		return null
	file.big_endian = false
	if file.get_32() != expected_sequence:
		return null
	var bytes := file.get_buffer(file.get_length() - 4)
	if bytes.size() < 4 or bytes[0] != 0xFF or bytes[1] != 0xD8:
		return null
	var image := Image.new()
	if image.load_jpg_from_buffer(bytes) != OK or image.get_size() != expected_size:
		return null
	return ImageTexture.create_from_image(image)
