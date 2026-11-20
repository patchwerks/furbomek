extends RefCounted

const Request = preload("res://effect_request.gd")
var crop := Rect2(0, 0, 1, 1)
var matched_id := ""
var reason := "fixed"

func resolve(request: RefCounted, snapshot: Dictionary, now_ms: int) -> Rect2:
	matched_id = ""
	if request.look == "rgb.fixed.v1":
		crop = Rect2(0, 0, 1, 1)
		reason = "fixed_rgb"
		return crop
	for rule in request.rules:
		match rule:
			"fixed":
				crop = Rect2(0, 0, 1, 1)
				reason = "fixed"
				return crop
			"hold":
				reason = "hold"
				return crop
			"subject":
				var age := now_ms - int(snapshot.get("produced_unix_ms", 0))
				if age < 0 or age > request.ttl_ms:
					continue
				for value in snapshot.get("tracks", []):
					if not value is Dictionary or value.get("id", "") != request.subject_id or value.get("kind", "") not in ["object", "body", "face"]:
						continue
					var box: Variant = value.get("optical_box")
					if not box is Array or box.size() != 4:
						continue
					var valid := true
					for coordinate in box:
						valid = valid and Request.number_in(coordinate, [0, 1])
					if not valid or box[2] <= 0 or box[3] <= 0 or box[0] + box[2] > 1 or box[1] + box[3] > 1:
						continue
					var span := clampf(maxf(float(box[2]), float(box[3])) * 1.6, 0.52, 1.0)
					var center := Vector2(box[0] + box[2] * 0.5, box[1] + box[3] * 0.5)
					crop = Rect2(center - Vector2.ONE * span * 0.5, Vector2.ONE * span)
					crop.position = crop.position.clamp(Vector2.ZERO, Vector2.ONE * (1.0 - span))
					matched_id = request.subject_id
					reason = "subject"
					return crop
	# No applicable rule holds the current frame, never picks another identity.
	reason = "hold_missing_subject"
	return crop
