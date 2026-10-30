extends SceneTree

# Real public Control consumer, fed only by broker-produced offline fixtures.
const ActivityPorts = preload("res://activity_ports.gd")
const STATES := ["IDLE", "THINKING", "SPEAKING", "INTERRUPTED", "ERROR", "ERROR"]


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		printerr("Expected one private fixture directory")
		quit(2)
		return
	var directory := arguments[0]
	var view = ActivityPorts.new()
	root.add_child(view)
	view.size = Vector2(1920, 1080)
	view.configure(directory)
	for index in STATES.size():
		var source := FileAccess.open(directory.path_join("case-%d.json" % index), FileAccess.READ)
		if source == null or source.get_length() > 65536:
			printerr("Missing or oversized broker fixture")
			quit(1)
			return
		var raw := source.get_as_text()
		source.close()
		var started := Time.get_ticks_usec()
		var output := FileAccess.open(directory.path_join("activity.json"), FileAccess.WRITE)
		if output == null:
			quit(1)
			return
		output.store_string(raw)
		output.close()
		view.last_poll = Time.get_ticks_msec() - view.POLL_MSEC
		view.tick()
		if view.activity.get("status", "") != STATES[index]:
			printerr("Broker fixture did not reach actual public Control: %s" % STATES[index])
			quit(1)
			return
		print("CHARACTER CONTROL %s apply_us=%d" % [STATES[index], Time.get_ticks_usec() - started])
		await process_frame
	# A new consumer reads the current snapshot without a private producer handle.
	var reconnected = ActivityPorts.new()
	root.add_child(reconnected)
	reconnected.configure(directory)
	reconnected.last_poll = Time.get_ticks_msec() - reconnected.POLL_MSEC
	reconnected.tick()
	if reconnected.activity.get("status", "") != "ERROR":
		printerr("New consumer failed to converge on current snapshot")
		quit(1)
		return
	print("CHARACTER CONTROL FIXTURES PASS (state application; rendered pixels unverified)")
	view.queue_free()
	reconnected.queue_free()
	quit(0)
