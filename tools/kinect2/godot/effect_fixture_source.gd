extends RefCounted

# Synthetic native slots are labelled fixture-only. Optical input may be a private replay.
static func snapshot(optical_path: String = "") -> Dictionary:
	var image := Image.create(1920, 1080, false, Image.FORMAT_RGB8)
	image.fill(Color(0.1, 0.2, 0.3))
	if not optical_path.is_empty():
		if image.load(optical_path) != OK or image.get_size() != Vector2i(1920, 1080):
			return {}
	var geometry := PackedFloat32Array()
	geometry.resize(217088 * 16)
	# The zero-alpha remainder deliberately represents holes, never filled by the viewer.
	for index in 1024:
		var offset := index * 16
		geometry[offset] = 1.0
		geometry[offset + 5] = 1.0
		geometry[offset + 10] = 1.0
		geometry[offset + 3] = float(index % 32) / 32.0 - 0.5
		geometry[offset + 7] = float(index / 32) / 32.0 - 0.5
		geometry[offset + 11] = -2.0
		geometry[offset + 12] = 0.8
		geometry[offset + 13] = 0.2
		geometry[offset + 14] = 0.1
		geometry[offset + 15] = 1.0
	var texture := ImageTexture.create_from_image(image)
	return {"sequence": 1, "count": 217088, "geometry": geometry,
		"registered": texture, "optical": texture, "tracks": [], "valid_points": 1024,
		"capture_fps": 0.0, "produced_unix_ms": int(Time.get_unix_time_from_system() * 1000), "ttl_ms": 600}
