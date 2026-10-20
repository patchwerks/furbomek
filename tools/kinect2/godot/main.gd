extends Node3D

const INITIAL_ZOOM := 2.15
const MIN_ZOOM := 0.65
const MAX_ZOOM := 5.0
const ORBIT_STEP := 0.075

@onready var orbit: Node3D = $Orbit
@onready var camera: Camera3D = $Orbit/Camera3D
@onready var cloud: MultiMeshInstance3D = $PointCloud
@onready var loader: Node = $StreamLoader
@onready var hud: Control = $Hud/BroadcastHUD
@onready var ports: Control = $Hud/ActivityPorts
@onready var color_surface: ColorRect = $Hud/ColorSurface

var mesh: MultiMesh
var material: ShaderMaterial
var zoom := INITIAL_ZOOM
var yaw := 0.0
var pitch := 0.0
var auto_orbit := false
var palette := 1
var point_pixels := 1.45
var sequence := -1
var color_mode := true
var source_valid := false


func _ready() -> void:
	if DisplayServer.get_name() != "headless":
		get_window().mode = Window.MODE_FULLSCREEN
	material = ShaderMaterial.new()
	material.shader = preload("res://point_cloud.gdshader")
	material.set_shader_parameter("palette_index", palette)
	material.set_shader_parameter("point_pixels", point_pixels)
	loader.snapshot_ready.connect(_apply_snapshot)
	loader.snapshot_expired.connect(_hide_stale)
	loader.configure(OS.get_environment("FURBOMEK_KINECT_DIR"))
	cloud.visible = false
	hud.set_camera(camera)
	hud.set_color_surface(color_surface)
	ports.configure(loader.stream_directory)
	_apply_camera()


func _process(delta: float) -> void:
	if auto_orbit:
		yaw = clampf(yaw + delta * 0.10, -0.36, 0.36)
		if absf(yaw) >= 0.35:
			auto_orbit = false
		_apply_camera()
	loader.tick()
	ports.tick()


func _apply_snapshot(snapshot: Dictionary) -> void:
	var count := int(snapshot["count"])
	if mesh == null or mesh.instance_count != count:
		mesh = MultiMesh.new()
		mesh.transform_format = MultiMesh.TRANSFORM_3D
		mesh.use_colors = true
		mesh.instance_count = count
		mesh.visible_instance_count = count
		mesh.mesh = _make_point_mesh()
		mesh.custom_aabb = AABB(Vector3(-8, -8, -12), Vector3(16, 16, 20))
		cloud.multimesh = mesh
	mesh.buffer = snapshot["geometry"]
	sequence = int(snapshot["sequence"])
	source_valid = true
	cloud.visible = not color_mode
	hud.set_snapshot(snapshot, _palette_name())
	color_surface.set_snapshot(snapshot, hud.get_selected_track())
	color_surface.set_active(color_mode)
	hud.set_color_mode(color_mode)
	ports.set_context(true, sequence, int(snapshot["valid_points"]), float(snapshot["capture_fps"]))


func _hide_stale() -> void:
	cloud.visible = false
	source_valid = false
	color_surface.clear_snapshot()
	hud.clear_snapshot()
	ports.set_context(false, sequence, 0, 0.0)


func _make_point_mesh() -> QuadMesh:
	var quad := QuadMesh.new()
	quad.size = Vector2.ONE
	quad.material = material
	return quad


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_ESCAPE: get_tree().quit()
			KEY_1: _set_palette(0)
			KEY_2: _set_palette(1)
			KEY_3: _set_palette(2)
			KEY_4:
				palette = 1
				material.set_shader_parameter("palette_index", palette)
				_use_native_view()
			KEY_BRACKETLEFT: _set_point_pixels(point_pixels - 0.15)
			KEY_BRACKETRIGHT: _set_point_pixels(point_pixels + 0.15)
			KEY_LEFT:
				_use_native_view()
				yaw = clampf(yaw - ORBIT_STEP, -0.55, 0.55)
			KEY_RIGHT:
				_use_native_view()
				yaw = clampf(yaw + ORBIT_STEP, -0.55, 0.55)
			KEY_UP:
				_use_native_view()
				pitch = clampf(pitch + ORBIT_STEP, -0.32, 0.32)
			KEY_DOWN:
				_use_native_view()
				pitch = clampf(pitch - ORBIT_STEP, -0.32, 0.32)
			KEY_O:
				_use_native_view()
				auto_orbit = not auto_orbit
			KEY_R:
				yaw = 0.0
				pitch = 0.0
				zoom = INITIAL_ZOOM
				auto_orbit = false
				color_surface.reset_view()
				_set_palette(1)
		_apply_camera()
		hud.set_palette_label(_palette_name())
	if event is InputEventMouseButton and event.pressed:
		if color_mode:
			if event.button_index == MOUSE_BUTTON_WHEEL_UP:
				color_surface.adjust_zoom(0.06)
			elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				color_surface.adjust_zoom(-0.06)
			hud.queue_redraw()
			return
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			zoom = clampf(zoom - 0.15, MIN_ZOOM, MAX_ZOOM)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			zoom = clampf(zoom + 0.15, MIN_ZOOM, MAX_ZOOM)
		_apply_camera()


func _apply_camera() -> void:
	orbit.rotation = Vector3(pitch, yaw, 0.0)
	camera.position = Vector3(0.0, 0.0, zoom)


func _set_palette(value: int) -> void:
	palette = value
	material.set_shader_parameter("palette_index", palette)
	color_mode = value != 2
	color_surface.set_palette(value)
	color_surface.set_active(color_mode)
	cloud.visible = not color_mode and source_valid
	hud.set_color_mode(color_mode)
	auto_orbit = false


func _use_native_view() -> void:
	color_mode = false
	color_surface.set_active(false)
	cloud.visible = source_valid
	hud.set_color_mode(false)


func _set_point_pixels(value: float) -> void:
	point_pixels = clampf(value, 0.75, 2.2)
	material.set_shader_parameter("point_pixels", point_pixels)
	color_surface.set_point_pixels(point_pixels)


func _palette_name() -> String:
	return ["RGB", "CRIMSON", "DEPTH"][palette] + (" SAMPLES" if color_mode else " XYZ")
