-- Para ingresar el plugin a Wireshark, copiar este archivo a la carpeta de plugins de Wireshark.
-- Ir a Help -> About Wireshark -> Folders -> Personal Plugins para ver la ruta(con doble click se accede a la carpeta).

local protocolo_tp1 = Proto("ProtocoloTP1", "Protocolo TP1")

-- Campos del protocolo
local f_seq_number = ProtoField.uint32("protocolo_tp1.seq_number", "Sequence Number", base.DEC)
local f_ack = ProtoField.bool("protocolo_tp1.ack", "ACK", nil, { "ACK", "Not an ACK" })
local f_syn = ProtoField.bool("protocolo_tp1.syn", "SYN", nil, { "SYN", "Not a SYN" })
local f_fin = ProtoField.bool("protocolo_tp1.fin", "FIN", nil, { "FIN", "Not a FIN" })
local f_datasize = ProtoField.uint32("protocolo_tp1.datasize", "Data Size", base.DEC)
local f_payload = ProtoField.bytes("protocolo_tp1.payload", "Payload")
local f_handshake_mode = ProtoField.uint32("protocolo_tp1.handshake.mode", "Error Recovery Mode", base.DEC)

-- Añado los campos al protocolo
protocolo_tp1.fields = { f_seq_number, f_ack, f_syn, f_fin, f_datasize, f_payload, f_handshake_mode }

function protocolo_tp1.dissector(buffer, pinfo, tree)
    local HEADER_SIZE = 7
    if buffer:len() < HEADER_SIZE then
        return
    end

    pinfo.cols.protocol = protocolo_tp1.name
    local subtree = tree:add(protocolo_tp1, buffer(), "Protocolo TP1")
    local offset = 0

    local seq_number_buffer = buffer:range(offset, 4)
    local seq_number = seq_number_buffer:uint()
    subtree:add(f_seq_number, seq_number_buffer)
    offset = offset + 4

    local ack_byte = buffer:range(offset, 1)
    local syn_byte = buffer:range(offset + 1, 1)
    local fin_byte = buffer:range(offset + 2, 1)
    subtree:add(f_ack, ack_byte, ack_byte:uint() ~= 0)
    subtree:add(f_syn, syn_byte, syn_byte:uint() ~= 0)
    subtree:add(f_fin, fin_byte, fin_byte:uint() ~= 0)
    offset = offset + 3

    local payload_size = buffer:len() - offset
    if payload_size > 0 then
        local payload_buffer = buffer:range(offset, payload_size)
        subtree:add(f_datasize, payload_size)
        
        if syn_byte:uint() ~= 0 and seq_number == 0 then
            subtree:add(f_handshake_mode, payload_buffer)
        else
            subtree:add(f_payload, payload_buffer)
        end
    end
end

-- Función que detecta automáticamente si un paquete UDP pertenece al protocolo
local function tp1_packet_detector(buffer, pinfo, tree)
    if buffer:len() < 7 then
        return false
    end


    local src_ip = tostring(pinfo.src)
    local dst_ip = tostring(pinfo.dst)
    local valid_ips = {"10.0.0.1", "10.0.0.2", "10.0.0.3"}
    
    local src_valid = false
    local dst_valid = false
    for _, ip in ipairs(valid_ips) do
        if src_ip == ip then src_valid = true end
        if dst_ip == ip then dst_valid = true end
    end
    
    if not (src_valid and dst_valid) then
        return false
    end

    local ack_byte = buffer:range(4,1):uint()
    local syn_byte = buffer:range(5,1):uint()
    local fin_byte = buffer:range(6,1):uint()

    if ack_byte > 1 or syn_byte > 1 or fin_byte > 1 then
        return false
    end

    protocolo_tp1.dissector(buffer, pinfo, tree)
    return true
end


-- Obtener las tablas de dissectores
local udp_port = DissectorTable.get("udp.port")

-- Conectamos el dissector principal solo al puerto de control fijo (si existe)
udp_port:add(6000, protocolo_tp1)

-- Registramos el heurístico para detectar el protocolo en cualquier puerto UDP
protocolo_tp1:register_heuristic("udp", tp1_packet_detector)