-- Real adapter boundary with no OBS instance or audio device.
local now = os.time() * 1000
obslua = {os_gettime_ns = function() return 1000000000 end}
dofile("tools/kinect2/effects/obs-effects.lua")
local good = {schema_version="furbomek.sfx.v1", consumer_id="1000000000", cue_id="fixture",
    owner="owner", expected_revision=0, revision=1, issued_ms=now,
    duration_ms=1000, preset="liquidation", gain_percent=100}
assert(validate_effect(good), "valid typed request rejected")
assert(apply_effect(good) == "muted", "default mute did not refuse playback")
for _, field in ipairs({"owner", "preset", "duration_ms", "consumer_id"}) do
    local old = good[field]; good[field] = nil
    assert(not validate_effect(good), "missing " .. field .. " accepted")
    good[field] = old
end
for _, bad in ipairs({-1, 101, "50", true, 0.5}) do
    good.gain_percent = bad
    assert(not validate_effect(good), "invalid gain accepted")
end
good.gain_percent = 100
good.preset = "../../private"
assert(not validate_effect(good), "arbitrary path accepted")
good.preset = "acknowledge"
good.command = "StartStream"
assert(not validate_effect(good), "arbitrary OBS command accepted")
good.command = nil
good.consumer_id = "old-consumer"
assert(apply_effect(good) == "conflict", "old consumer accepted")
good.consumer_id = "1000000000"
good.issued_ms = now - 2000
assert(apply_effect(good) == "expired_request", "stale request accepted")
print('{"passed":true,"assertions":15,"scope":"Lua boundary and default mute; no OBS playback qualification"}')
assert(decode_effect('{"gain_percent":50}').gain_percent == 50, "number decode")
assert(decode_effect('{"gain_percent":"50"}').gain_percent == "50", "string type preserved")
for _, raw in ipairs({'{"owner":"a","owner":"b"}', '{"owner":{}}', '{"gain_percent":NaN}', '{"gain_percent":1.5}', '{"gain_percent":1}evil', '{"owner":"a",}', '{"owner":"a\\n"}'}) do
    assert(decode_effect(raw) == nil, "malformed JSON accepted: " .. raw)
end
print('{"passed":true,"decoder_assertions":9}')
