local obs = obslua
local profile = "Furbomek Mac Test"
local mailbox = ""
local last_id = ""
local current = nil

local function private_ingest()
    local service = obs.obs_frontend_get_streaming_service()
    if service == nil then
        return false
    end
    local settings = obs.obs_service_get_settings(service)
    local key = obs.obs_data_get_string(settings, "key")
    local safe = obs.obs_data_get_string(settings, "service") == "Twitch"
        and obs.obs_data_get_bool(settings, "bwtest")
        and key:match("^[^?]+%?bandwidthtest=true$") ~= nil
    obs.obs_data_release(settings)
    return safe
end

local function dedicated_session()
    return obs.obs_frontend_get_current_profile() == profile
        and obs.obs_frontend_get_current_scene_collection() == profile
end

local function audio_is_muted()
    for slot = 1, 6 do
        local source = obs.obs_get_output_source(slot)
        if source ~= nil then
            local muted = obs.obs_source_muted(source)
            obs.obs_source_release(source)
            if not muted then
                return false
            end
        end
    end
    return true
end

local function find_viewer(source)
    local properties = obs.obs_source_properties(source)
    if properties == nil then
        return nil
    end
    local windows = obs.obs_properties_get(properties, "window")
    local selected = nil
    local count = 0
    if windows ~= nil then
        for index = 0, obs.obs_property_list_item_count(windows) - 1 do
            local name = obs.obs_property_list_item_name(windows, index)
            if name == "[Godot] Furb-o-Mek Kinect 2 Broadcast (DEBUG)"
                or name == "[Godot] Furb-o-Mek Kinect 2 Broadcast" then
                selected = obs.obs_property_list_item_int(windows, index)
                count = count + 1
            end
        end
    end
    obs.obs_properties_destroy(properties)
    return count == 1 and selected or nil
end

local function bind_window(source)
    local settings = obs.obs_source_get_settings(source)
    if obs.obs_data_get_int(settings, "type") ~= 1
        or not obs.obs_data_get_bool(settings, "show_hidden_windows") then
        obs.obs_data_set_int(settings, "type", 1)
        obs.obs_data_set_bool(settings, "show_hidden_windows", true)
        obs.obs_data_set_bool(settings, "show_cursor", false)
        obs.obs_source_update(source, settings)
    end
    local window = find_viewer(source)
    local bound = window ~= nil and window > 0
    if bound and obs.obs_data_get_int(settings, "window") ~= window then
        obs.obs_data_set_int(settings, "window", window)
        obs.obs_data_set_bool(settings, "show_cursor", false)
        obs.obs_source_update(source, settings)
        obs.obs_frontend_save()
    end
    obs.obs_data_release(settings)
    return bound
end

local function bind_source()
    if not dedicated_session() then
        return false
    end
    local scene_source = obs.obs_frontend_get_current_scene()
    if scene_source == nil then
        return false
    end
    local bound = false
    if obs.obs_source_get_name(scene_source) == "Kinect Program" then
        local items = obs.obs_scene_enum_items(obs.obs_scene_from_source(scene_source))
        if items ~= nil then
            if #items == 1 then
                local source = obs.obs_sceneitem_get_source(items[1])
                if obs.obs_source_get_name(source) == "Godot Furbomek Window"
                    and obs.obs_source_get_id(source) == "screen_capture"
                    and obs.obs_source_muted(source)
                    and obs.obs_sceneitem_visible(items[1]) then
                    bound = bind_window(source)
                end
            end
            obs.sceneitem_list_release(items)
        end
    end
    obs.obs_source_release(scene_source)
    return bound
end

local function response(request, result)
    local data = obs.obs_data_create()
    obs.obs_data_set_string(data, "request_id", request.id)
    obs.obs_data_set_string(data, "result", result)
    obs.obs_data_set_bool(data, "recording", obs.obs_frontend_recording_active())
    obs.obs_data_set_bool(data, "streaming", obs.obs_frontend_streaming_active())
    obs.obs_data_set_bool(data, "source_bound", request.bound)
    obs.obs_data_set_bool(data, "test_mode", dedicated_session() and private_ingest())
    local next_file = mailbox .. "/obs-response.next"
    local file = io.open(next_file, "w")
    if file ~= nil then
        file:write(obs.obs_data_get_json(data))
        file:close()
        os.rename(next_file, mailbox .. "/obs-response.json")
    end
    obs.obs_data_release(data)
end

local function read_request()
    local file = io.open(mailbox .. "/obs-request.json", "r")
    if file == nil then
        return nil
    end
    local raw = file:read(8193)
    file:close()
    if raw == nil or #raw > 8192 then
        return nil
    end
    local data = obs.obs_data_create_from_json(raw)
    if data == nil then
        return nil
    end
    local id = obs.obs_data_get_string(data, "request_id")
    local command = obs.obs_data_get_string(data, "command")
    local expires = obs.obs_data_get_int(data, "expires_at")
    obs.obs_data_release(data)
    if #id ~= 32 or not id:match("^[0-9a-f]+$") or id == last_id then
        return nil
    end
    last_id = id
    return {id = id, command = command, expires = expires, bound = false}
end

local function start_request(request)
    if not dedicated_session() or request.expires < os.time() or request.expires > os.time() + 5 then
        response(request, "refused")
        return
    end
    local command = request.command
    if command ~= "stop_streaming" and command ~= "stop_recording" then
        request.bound = bind_source()
    end
    if command == "status" then
        response(request, "ok")
    elseif command == "start_recording" and request.bound and audio_is_muted() then
        if not obs.obs_frontend_recording_active() then
            obs.obs_frontend_recording_start()
        end
        current = request
    elseif command == "stop_recording" then
        if obs.obs_frontend_recording_active() then
            obs.obs_frontend_recording_stop()
        end
        current = request
    elseif command == "start_test_stream" and request.bound and private_ingest() and audio_is_muted() then
        if obs.obs_frontend_streaming_active() then
            response(request, "ok")
        else
            obs.obs_frontend_streaming_start()
            response(request, "starting")
        end
    elseif command == "stop_streaming" then
        obs.obs_frontend_streaming_stop()
        response(request, "ok")
    else
        response(request, "refused")
    end
end

local function tick()
    if mailbox == "" then
        return
    end
    if current == nil then
        local request = read_request()
        if request ~= nil then
            start_request(request)
        end
        return
    end
    local command = current.command
    local recording = obs.obs_frontend_recording_active()
    if (command == "start_recording" and recording) or (command == "stop_recording" and not recording) then
        response(current, "ok")
        current = nil
    elseif current.expires < os.time() or not dedicated_session() then
        response(current, "unavailable")
        current = nil
    end
end

function script_update(settings)
    mailbox = obs.obs_data_get_string(settings, "mailbox")
end

function script_load(settings)
    script_update(settings)
    obs.timer_add(tick, 100)
end

function script_unload()
    obs.timer_remove(tick)
end
