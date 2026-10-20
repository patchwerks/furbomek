extends SceneTree

const ActivityEventReader = preload("res://activity_event_reader.gd")

var failures: Array[String] = []
var fixture_dir := ""
var reader = ActivityEventReader.new()


func _init() -> void:
	var directory := DirAccess.create_temp("furbomek-activity-fixtures-", false)
	if directory == null:
		_fail("fixture directory")
		quit(1)
		return
	fixture_dir = directory.get_current_dir()
	reader.configure(fixture_dir)
	_write_images()
	_run_cases(int(Time.get_unix_time_from_system() * 1000.0))
	_remove_fixtures()
	if failures.is_empty():
		print("ACTIVITY FIXTURES PASS")
		quit(0)
	else:
		printerr("ACTIVITY FIXTURES FAILED: %s" % [failures])
		quit(mini(failures.size(), 125))


func _run_cases(now_ms: int) -> void:
	_expect_valid_broker_event(now_ms)
	_expect_invalid_metadata(now_ms)
	_expect_v1_preview(now_ms)
	_expect_invalid_preview_and_timeline(now_ms)
	_expect_screen_rejections(now_ms)
	_expect_sequence_and_expiry(now_ms)
	_expect_privacy_release(now_ms)
	_expect_clearance_floors(now_ms)
	_expect_required_fields(now_ms)
	_expect_sequence_types(now_ms)
	_expect_timestamp_compatibility(now_ms)


func _expect_valid_broker_event(now_ms: int) -> void:
	var result := _publish(_event(1, now_ms, _payload()), now_ms)
	_expect(result.get("changed", false), "valid broker event changes state")
	var activity: Dictionary = result.get("activity", {})
	_expect(activity.get("title", "") == "FIXTURE-VALID" and activity.get("tool", "") == "BROWSER", "valid broker public payload survives")


func _expect_invalid_metadata(now_ms: int) -> void:
	var integer_observed := _event(2, now_ms, _payload())
	integer_observed["observedAt"] = now_ms
	_expect_empty(_publish(integer_observed, now_ms), "integer observedAt rejected")
	var unknown_source := _event(3, now_ms, _payload())
	unknown_source["source"] = "unknown-adapter"
	_expect_empty(_publish(unknown_source, now_ms), "unknown source rejected")
	var private_event := _event(4, now_ms, _payload())
	private_event["sensitivity"] = "private"
	_expect_empty(_publish(private_event, now_ms), "private event rejected")
	_write_text("activity.json", "x".repeat(65537))
	_expect_empty(reader.poll_at(now_ms), "oversized JSON rejected")


func _expect_v1_preview(now_ms: int) -> void:
	var payload := _payload()
	payload["image_filename"] = "legacy-preview.png"
	var result := _publish(_event(5, now_ms, payload), now_ms)
	_expect(result.get("activity", {}).get("_preview", null) != null, "v1 preview decodes")


func _expect_invalid_preview_and_timeline(now_ms: int) -> void:
	var invalid_preview := _payload()
	invalid_preview["image_filename"] = "../legacy-preview.png"
	_expect_empty(_publish(_event(6, now_ms, invalid_preview), now_ms), "malicious preview basename rejected")
	var invalid_timeline := _payload()
	invalid_timeline["timeline"] = [{"age_s": 86401, "category": "SYSTEM", "action": "CHECK", "detail": "BOUND", "status": "ok"}]
	_expect_empty(_publish(_event(7, now_ms, invalid_timeline), now_ms), "timeline bounds rejected")


func _expect_screen_rejections(now_ms: int) -> void:
	var oversized := PackedByteArray()
	oversized.resize(2097153)
	_write_bytes("hermes-screen-0.jpg", oversized)
	_expect_empty(_publish(_event(8, now_ms, _screen_payload("live", 1, 8, 6, now_ms)), now_ms), "oversized screen rejected")
	_write_bytes("hermes-screen-0.jpg", PackedByteArray([0, 1, 2, 3]))
	_expect_empty(_publish(_event(9, now_ms, _screen_payload("live", 1, 8, 6, now_ms)), now_ms), "bad JPEG rejected")
	_write_jpg("hermes-screen-0.jpg", Color(0.7, 0.1, 0.2))
	_expect_empty(_publish(_event(10, now_ms, _screen_payload("live", 2, 7, 6, now_ms)), now_ms), "dimension mismatch rejected")
	var stale := _publish(_event(11, now_ms, _screen_payload("live", 3, 8, 6, now_ms - 2001)), now_ms)
	_expect(not stale.get("activity", {}).is_empty() and stale.get("activity", {}).get("_screen_texture", null) == null, "stale screen clears texture")
	var future := _publish(_event(12, now_ms, _screen_payload("live", 4, 8, 6, now_ms + 1)), now_ms)
	_expect(not future.get("activity", {}).is_empty() and future.get("activity", {}).get("_screen_texture", null) == null, "future screen clears texture")


func _expect_sequence_and_expiry(now_ms: int) -> void:
	var accepted := _publish(_event(13, now_ms, _payload()), now_ms)
	_expect(not accepted.get("activity", {}).is_empty(), "newer sequence accepted")
	var duplicate_payload := _payload()
	duplicate_payload["title"] = "DUPLICATE"
	_expect_empty(_publish(_event(13, now_ms, duplicate_payload), now_ms), "duplicate sequence rejected")
	_expect_empty(_publish(_event(12, now_ms, _payload()), now_ms), "out-of-order sequence rejected")
	var expiring := _event(14, now_ms, _payload())
	expiring["ttlMs"] = 1
	_expect(not _publish(expiring, now_ms).get("activity", {}).is_empty(), "short-lived sequence accepted")
	_expect_empty(reader.poll_at(now_ms + 2), "unchanged JSON expires without revival")


func _expect_privacy_release(now_ms: int) -> void:
	_write_jpg("hermes-screen-0.jpg", Color(0.8, 0.15, 0.2))
	var live := _publish(_event(15, now_ms, _screen_payload("live", 10, 8, 6, now_ms)), now_ms)
	_expect(live.get("activity", {}).get("_screen_texture", null) != null, "fresh live screen decodes")
	var shuttered := _publish(_event(16, now_ms, _screen_payload("shuttered", 10, 8, 6, now_ms)), now_ms)
	_expect(shuttered.get("activity", {}).get("screen", {}).get("state", "") == "shuttered" and reader.screen_texture == null, "shutter clears cache")
	_expect_empty(_publish(_event(17, now_ms, _screen_payload("live", 10, 8, 6, now_ms)), now_ms), "privacy release rejects cached frame")
	_write_jpg("hermes-screen-0.jpg", Color(0.2, 0.15, 0.8))
	var released := _publish(_event(18, now_ms, _screen_payload("live", 11, 8, 6, now_ms)), now_ms)
	_expect(released.get("activity", {}).get("_screen_texture", null) != null, "privacy release requires fresh frame")
	var offline := _publish(_event(19, now_ms, _screen_payload("offline", 11, 8, 6, now_ms)), now_ms)
	_expect(offline.get("activity", {}).get("screen", {}).get("state", "") == "offline" and reader.screen_texture == null, "offline clears cache")
	DirAccess.remove_absolute(fixture_dir.path_join("activity.json"))
	_expect_empty(reader.poll_at(now_ms), "missing activity clears cache")


func _expect_clearance_floors(now_ms: int) -> void:
	_write_jpg("hermes-screen-0.jpg", Color(0.3, 0.1, 0.7))
	var present := _publish(_event(20, now_ms, _screen_payload("live", 30, 8, 6, now_ms)), now_ms)
	_expect(present.get("activity", {}).get("_screen_texture", null) != null, "live screen precedes absence")
	DirAccess.remove_absolute(fixture_dir.path_join("activity.json"))
	_expect_empty(reader.poll_at(now_ms), "absence clears active live screen")
	_expect_empty(_publish(_event(21, now_ms, _screen_payload("live", 30, 8, 6, now_ms)), now_ms), "absence blocks old screen sequence")
	var after_absence := _publish(_event(22, now_ms, _screen_payload("live", 31, 8, 6, now_ms)), now_ms)
	_expect(after_absence.get("activity", {}).get("_screen_texture", null) != null, "absence accepts newer screen sequence")
	var before_invalid := _publish(_event(23, now_ms, _screen_payload("live", 40, 8, 6, now_ms)), now_ms)
	_expect(before_invalid.get("activity", {}).get("_screen_texture", null) != null, "live screen precedes invalid JSON")
	_write_text("activity.json", "{")
	_expect_empty(reader.poll_at(now_ms), "invalid JSON clears active live screen")
	_expect_empty(_publish(_event(24, now_ms, _screen_payload("live", 40, 8, 6, now_ms)), now_ms), "invalid JSON blocks old screen sequence")
	var after_invalid := _publish(_event(25, now_ms, _screen_payload("live", 41, 8, 6, now_ms)), now_ms)
	_expect(after_invalid.get("activity", {}).get("_screen_texture", null) != null, "invalid JSON accepts newer screen sequence")


func _expect_required_fields(now_ms: int) -> void:
	var empty_title := _payload()
	empty_title["title"] = ""
	_expect_empty(_publish(_event(26, now_ms, empty_title), now_ms), "empty title rejected")
	var empty_status := _payload()
	empty_status["status"] = ""
	_expect_empty(_publish(_event(27, now_ms, empty_status), now_ms), "empty status rejected")
	var empty_tool := _payload()
	empty_tool["tool"] = ""
	_expect_empty(_publish(_event(28, now_ms, empty_tool), now_ms), "empty tool rejected")
	var empty_summary := _payload()
	empty_summary["summary"] = ""
	var result := _publish(_event(29, now_ms, empty_summary), now_ms)
	_expect(result.get("activity", {}).get("summary", "missing") == "", "empty summary accepted")


func _expect_sequence_types(now_ms: int) -> void:
	var negative := _event(30, now_ms, _payload())
	negative["seq"] = -1
	_expect_empty(_publish(negative, now_ms), "negative sequence rejected")
	var fractional := _event(31, now_ms, _payload())
	fractional["seq"] = 31.5
	_expect_empty(_publish(fractional, now_ms), "non-integer sequence rejected")


func _expect_timestamp_compatibility(now_ms: int) -> void:
	var seconds := _event(32, now_ms, _payload())
	seconds["observedAt"] = _utc_seconds(now_ms)
	_expect(not _publish(seconds, now_ms).get("activity", {}).is_empty(), "PLAN-shaped UTC seconds accepted")
	var short_fraction := _event(33, now_ms, _payload())
	short_fraction["observedAt"] = "%s.0Z" % _utc_seconds(now_ms).trim_suffix("Z")
	_expect(not _publish(short_fraction, now_ms).get("activity", {}).is_empty(), "one-digit fractional UTC accepted")
	var long_fraction := _event(34, now_ms, _payload())
	long_fraction["observedAt"] = "%s.000000001Z" % _utc_seconds(now_ms).trim_suffix("Z")
	_expect(not _publish(long_fraction, now_ms).get("activity", {}).is_empty(), "nine-digit fractional UTC accepted")


func _payload() -> Dictionary:
	return {"title": "FIXTURE-VALID", "summary": "PUBLIC-PAYLOAD", "status": "ACTING", "tool": "BROWSER"}


func _screen_payload(state: String, sequence: int, width: int, height: int, captured_at_ms: int) -> Dictionary:
	var payload := _payload()
	payload["screen"] = {"state": state, "filename": "hermes-screen-0.jpg", "seq": sequence, "width": width, "height": height, "captured_at_ms": captured_at_ms}
	return payload


func _event(sequence: int, now_ms: int, payload: Dictionary) -> Dictionary:
	return {"schemaVersion": "furbomek.character.v1", "kind": "agent.activity", "source": "hermes-adapter", "audience": "public", "sensitivity": "public", "seq": sequence, "observedAt": _utc_millis(now_ms), "ttlMs": 30000, "payload": payload}


func _publish(event: Dictionary, now_ms: int) -> Dictionary:
	_write_text("activity.json", JSON.stringify(event))
	return reader.poll_at(now_ms)


func _utc_millis(now_ms: int) -> String:
	return "%s.%03dZ" % [Time.get_datetime_string_from_unix_time(int(now_ms / 1000), false), posmod(now_ms, 1000)]


func _utc_seconds(now_ms: int) -> String:
	return "%sZ" % Time.get_datetime_string_from_unix_time(int(now_ms / 1000), false)


func _write_images() -> void:
	var preview := Image.create(4, 4, false, Image.FORMAT_RGBA8)
	preview.fill(Color(0.5, 0.1, 0.2, 1.0))
	preview.save_png(fixture_dir.path_join("legacy-preview.png"))
	_write_jpg("hermes-screen-0.jpg", Color(0.7, 0.1, 0.2))


func _write_jpg(name: String, color: Color) -> void:
	var image := Image.create(8, 6, false, Image.FORMAT_RGB8)
	image.fill(color)
	image.save_jpg(fixture_dir.path_join(name))


func _write_text(name: String, value: String) -> void:
	var file := FileAccess.open(fixture_dir.path_join(name), FileAccess.WRITE)
	file.store_string(value)


func _write_bytes(name: String, value: PackedByteArray) -> void:
	var file := FileAccess.open(fixture_dir.path_join(name), FileAccess.WRITE)
	file.store_buffer(value)


func _expect_empty(result: Dictionary, name: String) -> void:
	_expect(result.get("activity", {}).is_empty() and reader.preview == null and reader.screen_texture == null, name)


func _expect(condition: bool, name: String) -> void:
	if condition:
		print("PASS: %s" % name)
	else:
		_fail(name)


func _fail(name: String) -> void:
	failures.append(name)
	printerr("FAIL: %s" % name)


func _remove_fixtures() -> void:
	for name in ["activity.json", "legacy-preview.png", "hermes-screen-0.jpg"]:
		DirAccess.remove_absolute(fixture_dir.path_join(name))
	DirAccess.remove_absolute(fixture_dir)
