extends RefCounted

# Closed local boundary. No paths, shaders, OBS commands or provider text.
const FIELDS := ["schema_version", "consumer_id", "cue_id", "owner", "expected_revision", "revision", "issued_ms", "duration_ms", "look", "point_pixels", "zoom", "yaw", "pitch", "hud_visible", "insets_visible", "framing", "pulse_hz", "intensity_percent"]
const OPTIONAL := ["actor_id", "expected_owner", "operation", "preset"]
const LOOKS := ["rgb.fixed.v1", "rgb.crimson.v1", "xyz.depth.v1", "xyz.crimson.v1"]
var actor_id := "legacy"
var expected_owner: Variant = null
var operation := "apply"
var preset := "neutral"
var raw_value: Dictionary = {}
var roi := Rect2(0, 0, 1, 1)
var transition: Dictionary = {}
var valid_until_ms := 0
var fallback_roi := Rect2(0,0,1,1)
var consumer_id: String
var cue_id: String
var owner: String
var revision: int
var expected_revision: int
var issued_ms: int
var duration_ms: int
var look: String
var point_pixels: float
var zoom: float
var yaw: float
var pitch: float
var hud_visible: bool
var insets_visible: bool
var subject_id: String
var rules: Array[String] = []
var ttl_ms: int
var pulse_hz: float
var intensity_percent: int

static func parse(raw: String) -> RefCounted:
	if raw.length() > 8192:
		return null
	var value: Variant = JSON.parse_string(raw)
	if not value is Dictionary:
		return null
	for field in value:
		if field not in FIELDS and field not in OPTIONAL:
			return null
	if value.has("actor_id") and not identifier(value.actor_id):
		return null
	if value.has("expected_owner") and value.expected_owner != "" and not identifier(value.expected_owner):
		return null
	if value.get("operation", "apply") not in ["apply", "release", "stop"]:
		return null
	for field in FIELDS:
		if not value.has(field):
			return null
	if value.schema_version != "furbomek.effects.v1" or value.look not in LOOKS:
		return null
	if value.get("preset", "neutral") not in ["neutral", "rgb", "xyz", "liquidation"]: return null
	for field in ["consumer_id", "cue_id", "owner"]:
		if not identifier(value[field]):
			return null
	var ranges := {"expected_revision": [0, 2147483646], "revision": [1, 2147483647], "issued_ms": [1, 9007199254740991], "duration_ms": [1, 30000], "point_pixels": [0.75, 3.6], "zoom": [0.7, 1.5], "yaw": [-0.55, 0.55], "pitch": [-0.32, 0.32], "pulse_hz": [0, 1], "intensity_percent": [0, 100]}
	for field in ranges:
		var bounds: Array = ranges[field]
		if not number_in(value[field], bounds):
			return null
	for field in ["expected_revision", "revision", "issued_ms", "duration_ms", "intensity_percent"]:
		if float(value[field]) != floorf(float(value[field])):
			return null
	if not value.hud_visible is bool or not value.insets_visible is bool:
		return null
	var framing: Variant = value.framing
	if not framing is Dictionary or not framing.has_all(["subject_id", "rules", "ttl_ms"]):
		return null
	for field in framing:
		if field not in ["subject_id", "rules", "ttl_ms", "roi", "transition", "valid_until_ms", "fallback_roi"]:
			return null
	if not identifier(framing.subject_id) or not number_in(framing.ttl_ms, [1, 600]) or float(framing.ttl_ms) != floorf(float(framing.ttl_ms)):
		return null
	if not framing.rules is Array or framing.rules.is_empty() or framing.rules.size() > 3:
		return null
	var seen: Array[String] = []
	for rule in framing.rules:
		if rule not in ["subject", "fixed", "hold"] or rule in seen:
			return null
		seen.append(rule)
	var request = load("res://effect_request.gd").new()
	for field in FIELDS:
		if field not in ["schema_version", "framing"]:
			request.set(field, value[field])
	for field in ["expected_revision", "revision", "issued_ms", "duration_ms", "intensity_percent"]:
		value[field] = int(value[field])
	value.framing.ttl_ms = int(value.framing.ttl_ms)
	request.raw_value = value
	for field in OPTIONAL:
		if value.has(field): request.set(field, value[field])
	for roi_field in ["roi", "fallback_roi"]:
		if not framing.has(roi_field): continue
		var r: Variant = framing[roi_field]
		if not r is Dictionary or r.size() != 4 or not r.has_all(["x", "y", "width", "height"]): return null
		for coordinate in r.values():
			if not number_in(coordinate, [0, 1]): return null
		if r.width <= 0 or r.height <= 0 or r.x + r.width > 1 or r.y + r.height > 1: return null
		request.set(roi_field, Rect2(r.x, r.y, r.width, r.height))
	if framing.has("valid_until_ms"):
		if not number_in(framing.valid_until_ms, [0,9007199254740991]) or float(framing.valid_until_ms) != floorf(float(framing.valid_until_ms)): return null
		request.valid_until_ms = int(framing.valid_until_ms)
		request.raw_value.framing.valid_until_ms = request.valid_until_ms
		if request.valid_until_ms != 0 and (request.valid_until_ms < request.issued_ms or request.valid_until_ms > request.issued_ms + 600): return null
	if framing.get("transition") != null:
		var t: Variant = framing.transition
		var bounds := {"duration_ms": [100, 10000], "pan_units_per_second": [0.000001, 1], "zoom": [1, 4], "zoom_per_second": [0.000001, 1]}
		if not t is Dictionary or t.size() != bounds.size(): return null
		for field in bounds:
			if not t.has(field) or not number_in(t[field], bounds[field]): return null
		if float(t.duration_ms) != floorf(float(t.duration_ms)): return null
		t.duration_ms = int(t.duration_ms)
		request.transition = t
	request.subject_id = framing.subject_id
	request.rules.assign(seen)
	request.ttl_ms = int(framing.ttl_ms)
	return request

static func identifier(value: Variant) -> bool:
	if not value is String or value.is_empty() or value.length() > 64:
		return false
	var pattern := RegEx.new()
	pattern.compile("^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
	return pattern.search(value) != null

static func number_in(value: Variant, bounds: Array) -> bool:
	return (value is float or value is int) and is_finite(float(value)) and float(value) >= bounds[0] and float(value) <= bounds[1]
