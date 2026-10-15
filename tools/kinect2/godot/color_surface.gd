extends ColorRect

var shader_material: ShaderMaterial
var crop := Rect2(0.2, 0.2, 0.6, 0.6)
var anchor_id := ""
var zoom := 1.0
var active := true
var source_valid := false


func _ready() -> void:
	shader_material = ShaderMaterial.new()
	shader_material.shader = preload("res://color_surface.gdshader")
	material = shader_material
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	hide()


func set_snapshot(snapshot: Dictionary, track: Dictionary) -> void:
	var texture: Texture2D = snapshot.get("optical")
	if texture == null:
		hide()
		return
	var box_value = track.get("optical_box", [])
	if box_value is Array and box_value.size() == 4 and str(track.get("id", "")) != anchor_id:
		anchor_id = str(track.get("id", ""))
		var center := Vector2(float(box_value[0]) + float(box_value[2]) * 0.5, float(box_value[1]) + float(box_value[3]) * 0.5)
		var span := clampf(float(box_value[2]) / 0.45, 0.52, 0.9)
		crop = Rect2(center - Vector2(span * 0.47, span * 0.5), Vector2(span, span))
		crop.position.x = clampf(crop.position.x, 0.0, 1.0 - span)
		crop.position.y = clampf(crop.position.y, 0.0, 1.0 - span)
	shader_material.set_shader_parameter("optical_image", texture)
	if box_value is Array and box_value.size() == 4:
		shader_material.set_shader_parameter("subject_box", Vector4(float(box_value[0]), float(box_value[1]), float(box_value[2]), float(box_value[3])))
	else:
		shader_material.set_shader_parameter("subject_box", Vector4(-2, -2, 0, 0))
	_update_crop()
	source_valid = true
	visible = active


func set_active(value: bool) -> void:
	active = value
	visible = active and source_valid


func clear_snapshot() -> void:
	source_valid = false
	hide()


func set_palette(value: int) -> void:
	shader_material.set_shader_parameter("palette_index", value)


func set_point_pixels(value: float) -> void:
	shader_material.set_shader_parameter("point_pixels", value)


func adjust_zoom(amount: float) -> void:
	zoom = clampf(zoom + amount, 0.7, 1.5)
	_update_crop()


func reset_view() -> void:
	anchor_id = ""
	zoom = 1.0


func _update_crop() -> void:
	var span := clampf(crop.size.x / zoom, 0.3, 1.0)
	var current := Rect2(crop.get_center() - Vector2.ONE * span * 0.5, Vector2.ONE * span)
	current.position.x = clampf(current.position.x, 0.0, 1.0 - span)
	current.position.y = clampf(current.position.y, 0.0, 1.0 - span)
	shader_material.set_shader_parameter("source_crop", Vector4(current.position.x, current.position.y, span, span))
	set_meta("view_crop", current)


func project_optical(point: Vector2) -> Vector2:
	var current: Rect2 = get_meta("view_crop", crop)
	return (point - current.position) / current.size * get_viewport_rect().size


func project_box(box: Array) -> Rect2:
	if box.size() != 4:
		return Rect2()
	var first := project_optical(Vector2(float(box[0]), float(box[1])))
	var last := project_optical(Vector2(float(box[0]) + float(box[2]), float(box[1]) + float(box[3])))
	return Rect2(first, last - first)
