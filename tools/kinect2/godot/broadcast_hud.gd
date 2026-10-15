extends Control

const CRIMSON := Color("ec3e49")
const HOT := Color("ff4c55")
const TRACKER := Color("f15a8c")
const INK := Color("c69a9a")
const MUTED := Color("895158")
const AMBER := Color("ff9b42")
const PANEL := Color(0.08, 0.01, 0.025, 0.88)

var camera: Camera3D
var snapshot: Dictionary = {}
var selected_id := ""
var selected: Dictionary = {}
var palette_label := "CRIMSON"
var processed: TextureRect
var optical: TextureRect
var color_surface: ColorRect
var color_mode := true


func _ready() -> void:
	processed = _make_inset(1)
	optical = _make_inset(0)
	add_child(processed)
	add_child(optical)
	processed.hide()
	optical.hide()
	queue_redraw()


func set_camera(value: Camera3D) -> void:
	camera = value


func set_color_surface(value: ColorRect) -> void:
	color_surface = value


func set_color_mode(value: bool) -> void:
	color_mode = value
	queue_redraw()


func get_selected_track() -> Dictionary:
	return selected


func set_snapshot(value: Dictionary, next_palette: String) -> void:
	snapshot = value
	palette_label = next_palette
	selected = _select_track(value.get("tracks", []))
	_update_insets()
	queue_redraw()


func set_palette_label(value: String) -> void:
	palette_label = value
	queue_redraw()


func clear_snapshot() -> void:
	snapshot = {}
	selected = {}
	processed.hide()
	optical.hide()
	queue_redraw()


func _make_inset(style: int) -> TextureRect:
	var rect := TextureRect.new()
	rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	rect.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	var material := ShaderMaterial.new()
	material.shader = preload("res://inset.gdshader")
	material.set_shader_parameter("style", style)
	rect.material = material
	return rect


func _select_track(tracks: Array) -> Dictionary:
	var retained: Dictionary = {}
	var preferred: Dictionary = {}
	var preferred_rank := 9
	for track_value in tracks:
		if not track_value is Dictionary:
			continue
		var track: Dictionary = track_value
		if str(track.get("id", "")) == selected_id:
			retained = track
		var kind := str(track.get("kind", "surface"))
		var rank: int = int({"face": 0, "object": 1, "body": 2, "surface": 3}.get(kind, 8))
		if rank < preferred_rank:
			preferred = track
			preferred_rank = rank
	var retained_rank: int = int({"face": 0, "object": 1, "body": 2, "surface": 3}.get(str(retained.get("kind", "")), 8))
	if not retained.is_empty() and retained_rank <= preferred_rank:
		return retained
	if not preferred.is_empty():
		selected_id = str(preferred.get("id", ""))
	return preferred


func _update_insets() -> void:
	if selected.is_empty():
		processed.hide()
		optical.hide()
		return
	if color_mode:
		var optical_region = selected.get("optical_box")
		if not optical_region is Array or optical_region.size() != 4:
			processed.hide()
			optical.hide()
			return
		var region: Array = optical_region
		var probe = selected.get("probe_optical")
		if probe is Array and probe.size() == 2:
			var span := maxf(minf(float(region[2]), float(region[3]) * 1080.0 / 1920.0) * 0.40, 0.045)
			region = [float(probe[0]) - span * 0.5, float(probe[1]) - span * 0.5, span, span]
			_set_crop(processed, snapshot.get("optical"), region)
		else:
			processed.hide()
	else:
		_set_crop(processed, snapshot.get("registered"), selected.get("box", []))
	var optical_region = selected.get("optical_box")
	if optical_region is Array and optical_region.size() == 4:
		_set_crop(optical, snapshot.get("optical"), optical_region)
	else:
		optical.hide()


func _set_crop(target: TextureRect, texture: Texture2D, box: Array) -> void:
	if texture == null or box.size() != 4:
		target.hide()
		return
	var region := _normalized_rect(box, texture.get_size())
	if region.size.x < 2.0 or region.size.y < 2.0:
		target.hide()
		return
	target.texture = texture
	var crop_material: ShaderMaterial = target.material
	var dimensions := texture.get_size()
	crop_material.set_shader_parameter("source_region", Vector4(region.position.x / dimensions.x, region.position.y / dimensions.y, region.size.x / dimensions.x, region.size.y / dimensions.y))
	target.show()


func _draw() -> void:
	var scale := minf(size.x / 1920.0, size.y / 1080.0)
	var origin := (size - Vector2(1920, 1080) * scale) * 0.5
	draw_set_transform(origin, 0.0, Vector2(scale, scale))
	_draw_header()
	_draw_guides()
	_draw_panels()
	if snapshot.is_empty():
		_draw_text(Vector2(130, 560), "OFFLINE / AWAITING MATCHED SENSOR SNAPSHOT", 16, Color("7e2630"))
	else:
		_draw_tracking()
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


func _draw_header() -> void:
	_draw_text(Vector2(52, 54), "FURB-O-MEK / LIVE SENSOR ARRAY", 19, INK)
	_draw_text(Vector2(52, 77), "COLOR SAMPLES / DEPTH-PROBED TRACKS" if color_mode else "MEASURED XYZ / REGISTERED COLOR", 10, MUTED)
	var live_text := "LIVE / SEQ %06d / %s" % [int(snapshot.get("sequence", 0)), palette_label] if not snapshot.is_empty() else "OFFLINE / STALE HIDDEN"
	_draw_text(Vector2(1506, 54), live_text, 13, HOT if not snapshot.is_empty() else Color("7e2630"))
	draw_line(Vector2(52, 94), Vector2(1868, 94), Color(CRIMSON, 0.45), 2.0)


func _draw_guides() -> void:
	for y in [260.0, 545.0, 856.0]:
		draw_line(Vector2(176, y), Vector2(1372, y), Color(CRIMSON, 0.13), 1.0)
	for x in [46.0, 72.0, 98.0]:
		draw_line(Vector2(x, 900), Vector2(x, 930), Color(MUTED, 0.7), 2.0)
	draw_line(Vector2(46, 876), Vector2(46, 932), CRIMSON, 3.0)


func _draw_panels() -> void:
	var upper := Rect2(1415, 122, 430, 276)
	var lower := Rect2(1415, 434, 430, 276)
	_draw_panel(upper, "01 / TARGET MAGNIFICATION")
	_draw_text(Vector2(1430, 421), "ZOOM / LINKED SOURCE ROI", 10, MUTED)
	_draw_panel(lower, "02 / %s" % ("OPTICAL HEAD WINDOW" if str(selected.get("kind", "")) == "face" else "OPTICAL TARGET"))
	processed.position = upper.position + Vector2(7, 38)
	processed.size = upper.size - Vector2(14, 47)
	optical.position = lower.position + Vector2(7, 38)
	optical.size = lower.size - Vector2(14, 47)


func _draw_panel(rect: Rect2, title: String) -> void:
	draw_rect(rect, PANEL)
	draw_rect(Rect2(rect.position, Vector2(rect.size.x, 31)), Color("26070c"))
	var corners := PackedVector2Array([rect.position, Vector2(rect.end.x - 20, rect.position.y), Vector2(rect.end.x, rect.position.y + 20), rect.end, Vector2(rect.position.x, rect.end.y)])
	draw_polyline(corners, CRIMSON, 2.0)
	draw_line(Vector2(rect.position.x, rect.end.y), rect.position, CRIMSON, 2.0)
	_draw_text(rect.position + Vector2(13, 21), title, 12, INK)
	draw_rect(Rect2(rect.position + Vector2(13, rect.size.y - 13), Vector2(64, 4)), HOT)


func _draw_tracking() -> void:
	if selected.is_empty() or camera == null:
		return
	var box := _project_track()
	if box.size.x < 8.0 or box.size.y < 8.0:
		return
	_draw_corners(box, TRACKER, 30.0, 3.0)
	var label := "%s / %s" % [str(selected.get("label", selected.get("id", "TRACK"))).to_upper(), str(selected.get("id", "")).to_upper()]
	_draw_text(box.position + Vector2(0, -12), label, 15, INK)
	_draw_probe(box)


func _draw_probe(_track_box: Rect2) -> void:
	var point_value = selected.get("probe_world", [])
	if not point_value is Array or point_value.size() != 3:
		return
	var point: Array = point_value
	var projected := camera.unproject_position(Vector3(float(point[0]), float(point[1]), float(point[2])))
	if color_mode:
		var optical_value = selected.get("probe_optical")
		if not optical_value is Array or optical_value.size() != 2:
			return
		projected = color_surface.project_optical(Vector2(float(optical_value[0]), float(optical_value[1])))
	if projected.x < 0.0 or projected.y < 0.0 or projected.x > 1920.0 or projected.y > 1080.0:
		return
	var rect := Rect2(projected - Vector2(14, 10), Vector2(28, 20))
	_draw_corners(rect, AMBER, 9.0, 2.0)
	draw_circle(projected, 2.5, Color("ffe1b8"))
	draw_line(projected + Vector2(14, 0), Vector2(1415, 260), Color(AMBER, 0.60), 1.0)
	_draw_text(projected + Vector2(-28, 34), "SURFACE PROBE", 10, AMBER)
	_draw_text(projected + Vector2(-28, 47), "ACTUAL DEPTH SAMPLE", 9, MUTED)


func _project_track() -> Rect2:
	if color_mode and color_surface != null:
		var optical_region = selected.get("optical_box")
		if not optical_region is Array or optical_region.size() != 4:
			return Rect2()
		return color_surface.project_box(optical_region)
	var outline = selected.get("world_outline", [])
	if outline is Array and not outline.is_empty() and outline.size() <= 64:
		var result := Rect2()
		var started := false
		for sample in outline:
			if not sample is Array or sample.size() != 3:
				return Rect2()
			var position := Vector3(float(sample[0]), float(sample[1]), float(sample[2]))
			if camera.is_position_behind(position):
				continue
			var projected := camera.unproject_position(position)
			result = Rect2(projected, Vector2.ZERO) if not started else result.expand(projected)
			started = true
		return result
	return _project_world_box(selected.get("world_box", []))


func _project_world_box(values: Array) -> Rect2:
	if values.size() != 6:
		return Rect2()
	var minimum := Vector3(float(values[0]), float(values[1]), float(values[2]))
	var maximum := Vector3(float(values[3]), float(values[4]), float(values[5]))
	var bounds := Rect2()
	var initialized := false
	for x in [minimum.x, maximum.x]:
		for y in [minimum.y, maximum.y]:
			for z in [minimum.z, maximum.z]:
				var world := Vector3(x, y, z)
				if camera.is_position_behind(world):
					continue
				var screen := camera.unproject_position(world)
				bounds = Rect2(screen, Vector2.ZERO) if not initialized else bounds.expand(screen)
				initialized = true
	return bounds


func _draw_corners(rect: Rect2, color: Color, arm: float, width: float) -> void:
	var p := rect.position
	var e := rect.end
	for line in [[p, p + Vector2(arm, 0)], [p, p + Vector2(0, arm)], [Vector2(e.x - arm, p.y), Vector2(e.x, p.y)], [Vector2(e.x, p.y), Vector2(e.x, p.y + arm)], [Vector2(p.x, e.y - arm), Vector2(p.x, e.y)], [Vector2(p.x, e.y), Vector2(p.x + arm, e.y)], [Vector2(e.x - arm, e.y), e], [Vector2(e.x, e.y - arm), e]]:
		draw_line(line[0], line[1], color, width)


func _normalized_rect(box: Array, texture_size: Vector2) -> Rect2:
	var left := clampf(float(box[0]), 0.0, 1.0) * texture_size.x
	var top := clampf(float(box[1]), 0.0, 1.0) * texture_size.y
	var width := clampf(float(box[2]), 0.0, 1.0) * texture_size.x
	var height := clampf(float(box[3]), 0.0, 1.0) * texture_size.y
	return Rect2(left, top, minf(width, texture_size.x - left), minf(height, texture_size.y - top))


func _draw_text(position: Vector2, text: String, font_size: int, color: Color) -> void:
	draw_string(get_theme_default_font(), position, text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)
