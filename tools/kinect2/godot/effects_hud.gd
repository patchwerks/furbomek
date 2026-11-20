extends "res://broadcast_hud.gd"

var insets_enabled := true
var subject_lock := ""

func _draw_panels() -> void:
	if insets_enabled:
		super._draw_panels()

func _update_insets() -> void:
	if insets_enabled:
		super._update_insets()
	else:
		processed.hide()
		optical.hide()

func _select_track(tracks: Array, robot_only := false) -> Dictionary:
	if subject_lock.is_empty():
		return super._select_track(tracks, robot_only)
	for track in tracks:
		if track is Dictionary and track.get("id", "") == subject_lock and track.get("kind", "") in ["object", "body", "face"]:
			return track
	return {}
