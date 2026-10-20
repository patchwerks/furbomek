extends RefCounted

const SOURCES := ["hermes-adapter", "a2ui-adapter", "glimpse-adapter"]
const SCREEN_NAMES := ["hermes-screen-0.jpg", "hermes-screen-1.jpg"]


func parse_event(raw: String, now_ms: int) -> Dictionary:
	var parser := JSON.new()
	if parser.parse(raw) != OK:
		return {}
	var value = parser.data
	if not value is Dictionary:
		return {}
	var event: Dictionary = value
	if event.get("schemaVersion", "") != "furbomek.character.v1" or event.get("kind", "") != "agent.activity":
		return {}
	if not SOURCES.has(event.get("source", "")) or event.get("audience", "") != "public" or event.get("sensitivity", "") != "public":
		return {}
	if not _is_integer(event.get("seq", null)) or int(event["seq"]) < 0 or not _is_integer(event.get("ttlMs", null)):
		return {}
	var observed_ms := _observed_msec(event.get("observedAt", ""))
	var ttl_ms := int(event["ttlMs"])
	if ttl_ms <= 0 or ttl_ms > 30000 or observed_ms <= 0 or now_ms < observed_ms or now_ms - observed_ms > ttl_ms:
		return {}
	var payload_value = event.get("payload", {})
	if not payload_value is Dictionary:
		return {}
	var payload: Dictionary = payload_value
	var result: Dictionary = {"seq": int(event["seq"]), "expires_at_ms": observed_ms + ttl_ms}
	for key in ["title", "summary", "status", "tool"]:
		if not payload.get(key, null) is String or str(payload[key]).length() > 180:
			return {}
		if key != "summary" and str(payload[key]).is_empty():
			return {}
		result[key] = payload[key]
	if payload.has("image_filename"):
		if not payload["image_filename"] is String or not is_safe_preview_name(payload["image_filename"]):
			return {}
		result["image_filename"] = payload["image_filename"]
	if payload.has("timeline"):
		var timeline := _validate_timeline(payload["timeline"])
		if timeline.is_empty() and (not payload["timeline"] is Array or not payload["timeline"].is_empty()):
			return {}
		result["timeline"] = timeline
	if payload.has("screen"):
		var screen := _validate_screen(payload["screen"])
		if screen.is_empty():
			return {}
		result["screen"] = screen
	return result


func is_safe_preview_name(name: String) -> bool:
	return name.ends_with(".png") and not name.contains("/") and not name.contains("\\") and name.length() <= 96 and name.get_basename().is_valid_filename()


func _validate_timeline(value) -> Array:
	if not value is Array or value.size() > 6:
		return []
	var timeline: Array = value
	var result: Array = []
	for item_value in timeline:
		if not item_value is Dictionary:
			return []
		var item: Dictionary = item_value
		if not _is_integer(item.get("age_s", null)) or int(item["age_s"]) < 0 or int(item["age_s"]) > 86400:
			return []
		for key in ["category", "action", "detail"]:
			if not item.get(key, null) is String:
				return []
		if str(item["category"]).length() > 12 or str(item["action"]).length() > 48 or str(item["detail"]).length() > 60:
			return []
		if not ["ok", "error", "running"].has(item.get("status", "")):
			return []
		result.append({"age_s": int(item["age_s"]), "category": item["category"], "action": item["action"], "detail": item["detail"], "status": item["status"]})
	return result


func _validate_screen(value) -> Dictionary:
	if not value is Dictionary:
		return {}
	var screen: Dictionary = value
	if not ["live", "shuttered", "offline"].has(screen.get("state", "")) or not screen.get("filename", null) is String or not SCREEN_NAMES.has(screen["filename"]):
		return {}
	for key in ["seq", "width", "height", "captured_at_ms"]:
		if not _is_integer(screen.get(key, null)):
			return {}
	if int(screen["seq"]) < 0 or int(screen["width"]) < 1 or int(screen["width"]) > 1280 or int(screen["height"]) < 1 or int(screen["height"]) > 800 or int(screen["captured_at_ms"]) < 0:
		return {}
	return {"state": screen["state"], "filename": screen["filename"], "seq": int(screen["seq"]), "width": int(screen["width"]), "height": int(screen["height"]), "captured_at_ms": int(screen["captured_at_ms"])}


func _observed_msec(value) -> int:
	if not value is String:
		return 0
	var observed: String = value
	if observed.length() < 20 or observed.length() > 30 or observed.substr(4, 1) != "-" or observed.substr(7, 1) != "-" or observed.substr(10, 1) != "T" or observed.substr(13, 1) != ":" or observed.substr(16, 1) != ":" or not observed.ends_with("Z"):
		return 0
	var fractional := ""
	if observed.length() > 20:
		if observed.substr(19, 1) != ".":
			return 0
		fractional = observed.substr(20, observed.length() - 21)
		if fractional.is_empty() or fractional.length() > 9:
			return 0
		for index in fractional.length():
			var code := fractional.unicode_at(index)
			if code < 48 or code > 57:
				return 0
	for segment in [observed.substr(0, 4), observed.substr(5, 2), observed.substr(8, 2), observed.substr(11, 2), observed.substr(14, 2), observed.substr(17, 2)]:
		if not segment.is_valid_int():
			return 0
	var seconds := Time.get_unix_time_from_datetime_string(observed.left(19))
	var milliseconds := int(fractional.left(3).rpad(3, "0")) if not fractional.is_empty() else 0
	return int(seconds * 1000) + milliseconds


func _is_integer(value) -> bool:
	if not value is int and not value is float:
		return false
	var number := float(value)
	return is_finite(number) and floor(number) == number
