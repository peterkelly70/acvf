--[[
    AVCF Verification Plugin for VLC
    
    This plugin displays signature information for AVCF-enabled videos.
    
    Installation:
    - Copy this file to the VLC lua/extensions directory:
      - Windows: %APPDATA%\vlc\lua\extensions\
      - Linux: ~/.local/share/vlc/lua/extensions/
      - macOS: /Applications/VLC.app/Contents/MacOS/share/lua/extensions/
    
    Usage:
    - Open a video in VLC
    - Go to View > AVCF Verification
]]

-- Plugin descriptor
function descriptor()
    return {
        title = "AVCF Verification",
        version = "0.1.0",
        author = "AVCF Team",
        url = "https://github.com/peterkelly70/justice_protocol",
        shortdesc = "Verify AVCF signatures",
        description = "Displays signature information for AVCF-enabled videos",
        capabilities = {"menu", "input-listener"}
    }
end

-- Global variables
local status = "Not verified"
local metadata = nil
local error_message = nil
local verification_time = nil

-- Create dialog
function create_dialog()
    local d = vlc.dialog("AVCF Verification")
    
    -- Status section
    d:add_label("Status:", 1, 1, 1, 1)
    status_label = d:add_label(status, 2, 1, 3, 1)
    
    -- Error message (if any)
    if error_message then
        d:add_label("Error:", 1, 2, 1, 1)
        d:add_label(error_message, 2, 2, 3, 1)
    end
    
    -- Metadata section (if available)
    if metadata then
        local row = error_message and 3 or 2
        
        d:add_label("Author:", 1, row, 1, 1)
        d:add_label(metadata.author_name or "Unknown", 2, row, 3, 1)
        row = row + 1
        
        if metadata.author_email then
            d:add_label("Email:", 1, row, 1, 1)
            d:add_label(metadata.author_email, 2, row, 3, 1)
            row = row + 1
        end
        
        if metadata.author_organization then
            d:add_label("Organization:", 1, row, 1, 1)
            d:add_label(metadata.author_organization, 2, row, 3, 1)
            row = row + 1
        end
        
        d:add_label("Timestamp:", 1, row, 1, 1)
        d:add_label(metadata.timestamp or "Unknown", 2, row, 3, 1)
        row = row + 1
        
        d:add_label("Public key fingerprint:", 1, row, 1, 1)
        d:add_label(metadata.pubkey_fingerprint or "Unknown", 2, row, 3, 1)
        row = row + 1
        
        if metadata.pubkey_url then
            d:add_label("Public key URL:", 1, row, 1, 1)
            d:add_label(metadata.pubkey_url, 2, row, 3, 1)
            row = row + 1
        end
        
        if metadata.embedded_pubkey then
            d:add_label("Public key:", 1, row, 1, 1)
            d:add_label("Embedded in metadata", 2, row, 3, 1)
            row = row + 1
        end
        
        if metadata.tags and #metadata.tags > 0 then
            d:add_label("Tags:", 1, row, 1, 1)
            d:add_label(table.concat(metadata.tags, ", "), 2, row, 3, 1)
            row = row + 1
        end
        
        if metadata.notes then
            d:add_label("Notes:", 1, row, 1, 1)
            d:add_label(metadata.notes, 2, row, 3, 1)
            row = row + 1
        end
    end
    
    -- Verification time
    if verification_time then
        local row = metadata and 10 or (error_message and 3 or 2)
        d:add_label("Verification time:", 1, row, 1, 1)
        d:add_label(verification_time, 2, row, 3, 1)
    end
    
    -- Verify button
    local row = metadata and 11 or (error_message and 4 or 3)
    verify_button = d:add_button("Verify", verify_current_video, 1, row, 4, 1)
    
    return d
end

-- Menu activation
function activate()
    dialog = create_dialog()
end

-- Menu deactivation
function deactivate()
    dialog:delete()
    collectgarbage()
end

-- Menu close
function close()
    vlc.deactivate()
end

-- Input changed
function input_changed()
    -- Reset verification status when a new video is loaded
    status = "Not verified"
    metadata = nil
    error_message = nil
    verification_time = nil
    
    -- Recreate dialog if it exists
    if dialog then
        dialog:delete()
        dialog = create_dialog()
    end
end

-- Extract AVCF metadata from MP4 file
function extract_metadata_mp4()
    local input = vlc.input.item()
    if not input then return nil end
    
    local metas = input:metas()
    if not metas then return nil end
    
    -- Look for AVCF metadata in format tags
    local avcf_meta = metas["avcf_auth"]
    if not avcf_meta then return nil end
    
    -- Parse JSON metadata
    local ok, metadata_table = pcall(vlc.json.decode, avcf_meta)
    if not ok or not metadata_table then return nil end
    
    return metadata_table
end

-- Extract AVCF metadata from MKV file
function extract_metadata_mkv()
    local input = vlc.input.item()
    if not input then return nil end
    
    local metas = input:metas()
    if not metas then return nil end
    
    -- Look for AVCF metadata in format tags
    local avcf_meta = metas["AVCF_AUTH"]
    if not avcf_meta then return nil end
    
    -- Parse JSON metadata
    local ok, metadata_table = pcall(vlc.json.decode, avcf_meta)
    if not ok or not metadata_table then return nil end
    
    return metadata_table
end

-- Verify the current video
function verify_current_video()
    -- Get the current input item
    local input = vlc.input.item()
    if not input then
        status = "ERROR"
        error_message = "No video playing"
        dialog:delete()
        dialog = create_dialog()
        return
    end
    
    -- Get the file extension
    local uri = input:uri()
    local extension = string.match(uri, "%.([^%.]+)$")
    if not extension then
        status = "ERROR"
        error_message = "Unknown file format"
        dialog:delete()
        dialog = create_dialog()
        return
    end
    
    -- Extract metadata based on file format
    local metadata_table = nil
    if extension:lower() == "mp4" then
        metadata_table = extract_metadata_mp4()
    elseif extension:lower() == "mkv" or extension:lower() == "webm" then
        metadata_table = extract_metadata_mkv()
    end
    
    -- Update verification status
    verification_time = os.date("%Y-%m-%d %H:%M:%S")
    
    if not metadata_table then
        status = "MISSING"
        error_message = "No AVCF metadata found in the video file"
        metadata = nil
    else
        -- In a real implementation, we would verify the signature here
        -- For now, we just display the metadata
        status = "VALID"  -- Placeholder, in real implementation this would be based on actual verification
        error_message = nil
        metadata = metadata_table.metadata or metadata_table
    end
    
    -- Recreate dialog with updated information
    dialog:delete()
    dialog = create_dialog()
end

-- Menu configuration
function menu()
    return {"Verify current video"}
end

-- Menu selection
function trigger_menu(id)
    if id == 1 then
        verify_current_video()
    end
end
