extends RefCounted

# Closed local boundary. No paths, shaders, OBS commands or provider text.
const FIELDS := ["schema_version", "consumer_id", "cue_id", "owner", "expected_revision", "revision", "issued_ms", "duration_ms", "look", "point_pixels", "zoom", "yaw", "pitch", "hud_visible", "insets_visible", "framing", "pulse_hz", "intensity_percent"]
const LOOKS := ["rgb.fixed.v1", "rgb.crimson.v1", "xyz.depth.v1", "xyz.crimson.v1"]
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
	if not value is Dictionary or value.size() != FIELDS.size():
		return null
	for field in FIELDS:
		if not value.has(field):
			return null
	if value.schema_version != "furbomek.effects.v1" or value.look not in LOOKS:
		return null
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
	if not framing is Dictionary or framing.size() != 3 or not framing.has_all(["subject_id", "rules", "ttl_ms"]):
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
