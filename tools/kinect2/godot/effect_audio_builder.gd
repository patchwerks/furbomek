extends SceneTree

# Original synthesized tones, never a microphone or external asset.
func _init() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		quit(2)
		return
	for preset in ["liquidation", "acknowledge"]:
		var data := PackedByteArray()
		data.resize(24000 * 2)
		var peak := 0
		for index in 24000:
			var time := float(index) / 48000.0
			var envelope := sin(PI * float(index) / 23999.0)
			var frequency := 330.0 if preset == "liquidation" else 660.0
			var sample := int(sin(TAU * frequency * time) * envelope * 8000.0)
			peak = maxi(peak, absi(sample))
			data.encode_s16(index * 2, sample)
		var audio := AudioStreamWAV.new()
		audio.format = AudioStreamWAV.FORMAT_16_BITS
		audio.mix_rate = 48000
		audio.stereo = false
		audio.data = data
		var result := audio.save_to_wav(arguments[0].path_join(preset + ".wav"))
		print(JSON.stringify({"preset": preset, "peak_sample": peak, "peak_dbfs": linear_to_db(float(peak) / 32768.0), "frames": 24000, "save_error": result}))
		if result != OK or peak > 8230:
			quit(1)
			return
	quit(0)
