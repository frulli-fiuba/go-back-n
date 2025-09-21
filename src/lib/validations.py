import os
import socket
import sys
from lib.constants import ERROR_RECOVERY_PROTOCOL_MAPPING


def validate_host(host):
    """Valida que el host sea una dirección IP válida o un hostname válido."""
    if host is None:
        return False

    try:
        socket.gethostbyname(host)
        return True
    except socket.gaierror:
        return False


def validate_port(port):
    """Valida que el puerto esté en el rango válido (1-65535)."""
    if port is None:
        return False

    return 1 <= port <= 65535


def validate_protocol(protocol):
    """Valida que el protocolo sea uno de los valores permitidos."""
    if protocol is None:
        return True

    if protocol not in ERROR_RECOVERY_PROTOCOL_MAPPING.keys():
        return False
    
    return True


def validate_src_file(src_path):
    """Valida que el archivo de origen exista y sea legible."""
    if src_path is None:
        return False
    
    if not os.path.exists(src_path):
        return False
    
    if not os.path.isfile(src_path):
        return False
    
    if not os.access(src_path, os.R_OK):
        return False
    
    return True


def validate_file_name(name):
    """Valida que el nombre de archivo sea válido."""
    if name is None:
        return True  # El nombre es opcional en algunos casos

    # Caracteres no permitidos en nombres de archivo
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    
    if any(char in name for char in invalid_chars):
        return False
    
    # No puede estar vacío
    if not name.strip():
        return False
    
    # No puede ser solo puntos
    if name.strip() in ['.', '..']:
        return False
    
    return True


def validate_storage_dir(storage_path):
    """Valida que el directorio de almacenamiento exista y sea escribible."""
    if storage_path is None:
        return False
    
    if not os.path.exists(storage_path):
        return False
    
    if not os.path.isdir(storage_path):
        return False
    
    if not os.access(storage_path, os.W_OK):
        return False
    
    return True


def validate_destination_dir(dest_path):
    """Valida que el directorio de destino exista y sea escribible."""
    if dest_path is None:
        return False
    
    # Si es un archivo, validar el directorio padre
    if os.path.isfile(dest_path):
        dest_dir = os.path.dirname(dest_path)
    else:
        dest_dir = dest_path
    
    if not os.path.exists(dest_dir):
        return False
    
    if not os.path.isdir(dest_dir):
        return False
    
    if not os.access(dest_dir, os.W_OK):
        return False
    
    return True


def _base_validations(args):
    """Validaciones base: host y port."""
    errors = []
    
    if not validate_host(args.host):
        errors.append(f"Host inválido: '{args.host}'. Debe ser una dirección IP válida o un hostname resoluble.")
    
    if not validate_port(args.port):
        errors.append(f"Puerto inválido: {args.port}. Debe estar entre 1 y 65535.")
    
    return errors


def server_validations(args):
    """Validaciones para el servidor: base + storage."""
    errors = _base_validations(args)
    
    if hasattr(args, 'storage') and not validate_storage_dir(args.storage):
        if not os.path.exists(args.storage):
            errors.append(f"Directorio de almacenamiento no encontrado: '{args.storage}'.")
        elif not os.path.isdir(args.storage):
            errors.append(f"La ruta especificada no es un directorio: '{args.storage}'.")
        elif not os.access(args.storage, os.W_OK):
            errors.append(f"No se puede escribir en el directorio de almacenamiento: '{args.storage}'. Verifique los permisos.")
        else:
            errors.append(f"Directorio de almacenamiento inválido: '{args.storage}'.")
    
    if errors:
        print("Errores de validación del servidor:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


def upload_validations(args):
    """Validaciones para upload: base + src + name + protocol."""
    errors = _base_validations(args)
    
    if not validate_protocol(args.protocol):
        protocol_list = ", ".join(ERROR_RECOVERY_PROTOCOL_MAPPING.keys())
        errors.append(f"Protocolo inválido: '{args.protocol}'. Debe ser uno de: {protocol_list}.")
    
    if hasattr(args, 'src') and not validate_src_file(args.src):
        if not os.path.exists(args.src):
            errors.append(f"Archivo de origen no encontrado: '{args.src}'.")
        elif not os.path.isfile(args.src):
            errors.append(f"La ruta especificada no es un archivo: '{args.src}'.")
        elif not os.access(args.src, os.R_OK):
            errors.append(f"No se puede leer el archivo de origen: '{args.src}'. Verifique los permisos.")
        else:
            errors.append(f"Archivo de origen inválido: '{args.src}'.")
    
    if hasattr(args, 'name') and args.name and not validate_file_name(args.name):
        if not args.name.strip():
            errors.append("El nombre de archivo no puede estar vacío.")
        elif args.name.strip() in ['.', '..']:
            errors.append("El nombre de archivo no puede ser '.' o '..'.")
        else:
            errors.append(f"Nombre de archivo inválido: '{args.name}'. Contiene caracteres no permitidos.")
    
    if errors:
        print("Errores de validación de upload:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


def download_validations(args):
    """Validaciones para download: base + destination + name + protocol."""
    errors = _base_validations(args)
    
    if not validate_protocol(args.protocol):
        protocol_list = ", ".join(ERROR_RECOVERY_PROTOCOL_MAPPING.keys())
        errors.append(f"Protocolo inválido: '{args.protocol}'. Debe ser uno de: {protocol_list}.")
    
    if hasattr(args, 'destination') and not validate_destination_dir(args.destination):
        dest_dir = os.path.dirname(args.destination) if os.path.isfile(args.destination) else args.destination
        if not os.path.exists(dest_dir):
            errors.append(f"Directorio de destino no encontrado: '{dest_dir}'.")
        elif not os.path.isdir(dest_dir):
            errors.append(f"La ruta especificada no es un directorio: '{dest_dir}'.")
        elif not os.access(dest_dir, os.W_OK):
            errors.append(f"No se puede escribir en el directorio de destino: '{dest_dir}'. Verifique los permisos.")
        else:
            errors.append(f"Directorio de destino inválido: '{args.destination}'.")
    
    if hasattr(args, 'name') and args.name and not validate_file_name(args.name):
        if not args.name.strip():
            errors.append("El nombre de archivo no puede estar vacío.")
        elif args.name.strip() in ['.', '..']:
            errors.append("El nombre de archivo no puede ser '.' o '..'.")
        else:
            errors.append(f"Nombre de archivo inválido: '{args.name}'. Contiene caracteres no permitidos.")
    
    if errors:
        print("Errores de validación de download:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
