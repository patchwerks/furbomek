-- Candidate adapter: a pre-provisioned source in the dedicated private scene only.
-- No source creation, device capture, profile mutation or streaming authority.
local obs = obslua
local revision, expires, last_raw = 0, 0, ""
local muted, mailbox, assets = true, "", ""
local consumer_id = tostring(obs.os_gettime_ns())
local active_owner, active_cue, actor_id = "", "", ""
local active_preset, active_gain, active_duration = "acknowledge", 0, 1000
local playback_status, submitted_at = "ready", 0
local active_source = nil
local fields = {schema_version=true, consumer_id=true, cue_id=true, owner=true,
    expected_revision=true, revision=true, issued_ms=true, duration_ms=true,
    preset=true, gain_percent=true, actor_id=true, expected_owner=true, operation=true}

local function identifier(value)
    return type(value) == "string" and #value >= 1 and #value <= 64
        and value:match("^[%w][%w_.-]*$") ~= nil
end

local function integer(value, low, high)
    return type(value) == "number" and value == math.floor(value)
        and value >= low and value <= high
end

-- This flat protocol deliberately accepts only identifier strings and decimal integers.
-- Nested objects, escapes, duplicate keys and non-finite numbers cannot reach OBS.
function decode_effect(raw)
    if type(raw) ~= "string" or #raw > 8192 then return nil end
    local cursor, result = 1, {}
    local function space()
        local _, last = raw:find("^%s*", cursor)
        cursor = last + 1
    end
    local function take(character)
        space()
        if raw:sub(cursor, cursor) ~= character then return false end
        cursor = cursor + 1
        return true
    end
    local function word()
        space()
        local first, last, value = raw:find('^"([%w_.-]+)"', cursor)
        if first == nil then return nil end
        cursor = last + 1
        return value
    end
    if not take("{") then return nil end
    repeat
        local key = word()
        if key == nil or result[key] ~= nil or not take(":") then return nil end
        space()
        local value = word()
        if value == nil then
            local first, last, number = raw:find("^(%-?%d+)", cursor)
            if first == nil then return nil end
            cursor, value = last + 1, tonumber(number)
        end
        result[key] = value
        space()
        if raw:sub(cursor, cursor) == "}" then
            cursor = cursor + 1; space()
            return cursor > #raw and result or nil
        end
    until not take(",")
    return nil
end

function validate_effect(request)
    if type(request) ~= "table" then return false end
    local count = 0
    for name in pairs(request) do
        if not fields[name] then return false end
        count = count + 1
    end
    return (count == 10 or (count == 13 and identifier(request.actor_id)
        and identifier(request.expected_owner) and (request.operation == "apply" or request.operation == "stop"))) and request.schema_version == "furbomek.sfx.v1"
        and identifier(request.consumer_id) and identifier(request.cue_id) and identifier(request.owner)
        and integer(request.expected_revision, 0, 2147483646)
        and integer(request.revision, 1, 2147483647)
        and integer(request.issued_ms, 1, 9007199254740991)
        and request.issued_ms % 1000 == 0
        and integer(request.duration_ms, 1, 30000)
        and integer(request.gain_percent, 0, 100)
        and (request.preset == "liquidation" or request.preset == "acknowledge")
end

local function source()
    if obs.obs_frontend_get_current_profile() ~= "Furbomek Mac Test"
        or obs.obs_frontend_get_current_scene_collection() ~= "Furbomek Mac Test" then return nil end
    local scene = obs.obs_frontend_get_current_scene()
    if scene == nil then return nil end
    local found = nil
    if obs.obs_source_get_name(scene) == "Kinect Program" then
        local item = obs.obs_scene_find_source(obs.obs_scene_from_source(scene), "Furbomek Program SFX")
        if item ~= nil and obs.obs_sceneitem_visible(item) then
            local candidate = obs.obs_sceneitem_get_source(item)
            if obs.obs_source_get_id(candidate) == "ffmpeg_source" then
                found = obs.obs_source_get_ref(candidate)
            end
        end
    end
    obs.obs_source_release(scene)
    return found
end

local function stop_audio()
    local input = active_source or source()
    if input ~= nil then
        obs.obs_source_set_muted(input, true)
        obs.obs_source_media_stop(input)
        obs.obs_source_release(input)
    end
    active_source = nil
    expires = 0
    active_owner, active_cue, actor_id = "", "", ""
end

local function receipt(status)
    if mailbox == "" then return end
    local data = obs.obs_data_create()
    obs.obs_data_set_string(data, "schema_version", "furbomek.sfx-ack.v1")
    obs.obs_data_set_string(data, "consumer_id", consumer_id)
    obs.obs_data_set_string(data, "status", status)
    obs.obs_data_set_string(data, "actor_id", actor_id)
    obs.obs_data_set_int(data, "published_ms", os.time() * 1000)
    obs.obs_data_set_string(data, "preset", active_preset)
    obs.obs_data_set_int(data, "gain_percent", active_gain)
    obs.obs_data_set_int(data, "duration_ms", active_duration)
    local available = source()
    obs.obs_data_set_bool(data, "source_available", available ~= nil and assets ~= "")
    if available ~= nil then obs.obs_source_release(available) end
    obs.obs_data_set_string(data, "owner", active_owner)
    obs.obs_data_set_string(data, "cue_id", active_cue)
    obs.obs_data_set_int(data, "revision", revision)
    obs.obs_data_set_bool(data, "muted", muted)
    local file = io.open(mailbox .. "/sfx-ack.next", "w")
    if file ~= nil then
        file:write(obs.obs_data_get_json(data)); file:close()
        os.rename(mailbox .. "/sfx-ack.next", mailbox .. "/sfx-ack.json")
    end
    obs.obs_data_release(data)
end

function apply_effect(request)
    if not validate_effect(request) then return "invalid" end
    if request.consumer_id ~= consumer_id or request.expected_revision ~= revision
        or request.revision ~= revision + 1 then return "conflict" end
    if request.expected_owner ~= nil and request.expected_owner ~= (active_owner ~= "" and active_owner or "none") then return "owner_conflict" end
    if request.operation == "stop" then
        if request.actor_id ~= actor_id then return "owner_conflict" end
        stop_audio(); revision = request.revision; playback_status = "stopped"
        return "stopped"
    end
    local age = os.time() * 1000 - request.issued_ms
    if age < 0 or age > 1000 or age >= request.duration_ms then return "expired_request" end
    if muted then return "muted" end
    local media = io.open(assets .. "/" .. request.preset .. ".wav", "rb")
    if media == nil then return "source_unavailable" end
    media:close()
    stop_audio()
    local input = source()
    if input == nil or assets == "" then
        if input ~= nil then obs.obs_source_release(input) end
        return "source_unavailable"
    end
    local settings = obs.obs_data_create()
    obs.obs_data_set_bool(settings, "is_local_file", true)
    obs.obs_data_set_bool(settings, "looping", false)
    obs.obs_data_set_string(settings, "local_file", assets .. "/" .. request.preset .. ".wav")
    obs.obs_source_update(input, settings)
    obs.obs_data_release(settings)
    obs.obs_source_set_volume(input, 0.251188643 * request.gain_percent / 100)
    obs.obs_source_set_monitoring_type(input, obs.OBS_MONITORING_TYPE_NONE)
    obs.obs_source_set_muted(input, false)
    obs.obs_source_media_restart(input)
    active_source = input
    revision, active_owner, active_cue = request.revision, request.owner, request.cue_id
    actor_id = request.actor_id or "legacy"
    active_preset, active_gain, active_duration = request.preset, request.gain_percent, request.duration_ms
    submitted_at = obs.os_gettime_ns()
    playback_status = "submitted"
    expires = obs.os_gettime_ns() + (request.duration_ms - age) * 1000000
    return "submitted"
end

local function tick()
    if active_source ~= nil then
        local state = obs.obs_source_media_get_state(active_source)
        if state == obs.OBS_MEDIA_STATE_PLAYING and not obs.obs_source_muted(active_source) then
            playback_status = "playing"
        elseif (state == obs.OBS_MEDIA_STATE_OPENING or state == obs.OBS_MEDIA_STATE_BUFFERING)
            and not obs.obs_source_muted(active_source)
            and obs.os_gettime_ns() - submitted_at <= 500000000 then
            playback_status = "submitted"
        else
            stop_audio(); revision = revision + 1; playback_status = "playback_unavailable"
        end
    end
	if active_source ~= nil then
		local current = source()
		if current == nil or current ~= active_source then
            if current ~= nil then obs.obs_source_release(current) end
            stop_audio(); revision = revision + 1; playback_status = "source_lost"; receipt(playback_status)
		else obs.obs_source_release(current) end
	end
    if expires > 0 and (muted or obs.os_gettime_ns() >= expires) then
        stop_audio(); revision = revision + 1; playback_status = "expired"; receipt(playback_status)
    end
    receipt(playback_status)
    if mailbox == "" then return end
    local file = io.open(mailbox .. "/sfx.json", "r")
    if file == nil then return end
    local raw = file:read(8193); file:close()
    if raw == nil or raw == last_raw then return end
    last_raw = raw
    if #raw > 8192 then receipt("invalid"); return end
    local outcome = apply_effect(decode_effect(raw))
    receipt(outcome)
end

function script_defaults(settings)
    obs.obs_data_set_default_bool(settings, "muted", true)
end
function script_update(settings)
    local was_muted = muted
    muted = not obs.obs_data_has_user_value(settings, "muted") or obs.obs_data_get_bool(settings, "muted")
    mailbox = obs.obs_data_get_string(settings, "mailbox")
    assets = obs.obs_data_get_string(settings, "assets")
    if muted then
        stop_audio()
        if not was_muted then revision = revision + 1 end
    end
    playback_status = muted and "muted" or "ready"
    receipt(playback_status)
end
function script_load(settings)
    script_update(settings); obs.timer_add(tick, 50)
end
function script_unload()
    stop_audio(); obs.timer_remove(tick)
end
