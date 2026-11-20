-- Real Lua adapter with a deterministic OBS API fixture; no audio qualification.
local clock, state, mute = 1000000000, 1, true
local timer, receipt_value, restarted = nil, nil, 0
local directory = assert(arg[1], "private fixture directory required")
local settings = {muted=false, mailbox=directory, assets=directory}
local input, scene = {}, {}
obslua = {
    OBS_MEDIA_STATE_OPENING=1, OBS_MEDIA_STATE_BUFFERING=6, OBS_MEDIA_STATE_PLAYING=2, OBS_MEDIA_STATE_ERROR=3, OBS_MEDIA_STATE_ENDED=4,
    OBS_MEDIA_STATE_STOPPED=5, OBS_MONITORING_TYPE_NONE=0,
    os_gettime_ns=function() return clock end,
    obs_frontend_get_current_profile=function() return "Furbomek Mac Test" end,
    obs_frontend_get_current_scene_collection=function() return "Furbomek Mac Test" end,
    obs_frontend_get_current_scene=function() return scene end,
    obs_source_get_name=function() return "Kinect Program" end,
    obs_scene_from_source=function() return scene end,
    obs_scene_find_source=function() return input end,
    obs_sceneitem_visible=function() return true end,
    obs_sceneitem_get_source=function() return input end,
    obs_source_get_id=function() return "ffmpeg_source" end,
    obs_source_get_ref=function() return input end,
    obs_source_release=function() end,
    obs_source_set_muted=function(_, value) mute=value end,
    obs_source_muted=function() return mute end,
    obs_source_media_stop=function() state=5 end,
    obs_source_media_restart=function() restarted=restarted+1; state=1 end,
    obs_source_media_get_state=function() return state end,
    obs_source_set_volume=function() end,
    obs_source_set_monitoring_type=function() end,
    obs_source_update=function() end,
    obs_data_create=function() return {} end,
    obs_data_release=function() end,
    obs_data_get_json=function(value) receipt_value=value; return "{}" end,
    obs_data_get_string=function(value, key) return value[key] end,
    obs_data_get_bool=function(value, key) return value[key] end,
    obs_data_has_user_value=function(value, key) return value[key] ~= nil end,
    timer_add=function(callback) timer=callback end,
    timer_remove=function() end,
}
for _, name in ipairs({"string", "int", "bool"}) do
    obslua["obs_data_set_"..name] = function(value, key, item) value[key]=item end
end
dofile("tools/kinect2/effects/obs-effects.lua")
script_load(settings)
local request={schema_version="furbomek.sfx.v1", consumer_id="1000000000",
    actor_id="fixture", cue_id="cue", owner="owner", expected_owner="none",
    expected_revision=0, revision=1, issued_ms=os.time()*1000, duration_ms=3000,
    preset="acknowledge", gain_percent=50, operation="apply"}
assert(apply_effect(request)=="submitted" and restarted==1, "restart must only submit")
assert(timer)
timer()
assert(receipt_value.status=="submitted", "opening cannot acknowledge playback")
state=2; timer()
assert(receipt_value.status=="playing" and receipt_value.owner=="owner", "actual playing state required")
request.expected_revision=1; request.revision=2; request.expected_owner="other"
assert(apply_effect(request)=="owner_conflict", "stale owner must fail")
request.expected_owner="owner"; request.operation="stop"; request.actor_id="other"
assert(apply_effect(request)=="owner_conflict", "foreign actor stop must fail")
request.actor_id="fixture"
assert(apply_effect(request)=="stopped" and mute, "owner stop must mute")
request.expected_revision=2; request.revision=3; request.expected_owner="none"; request.operation="apply"
assert(apply_effect(request)=="submitted")
clock=clock+600000000; timer()
assert(receipt_value.status=="playback_unavailable" and mute, "bounded opening timeout must hold")
script_unload()
print('{"passed":true,"scope":"actual Lua adapter against OBS API fixture; playback capture HOLD","assertions":8}')
