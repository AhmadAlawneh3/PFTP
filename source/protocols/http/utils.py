"""HTTP-specific utility functions for file operations, network detection, and metadata"""

import os
import json
import datetime
import mimetypes
import subprocess


def get_all_interfaces():
    """Get all interface IP addresses, prioritizing tun0 and eth interfaces"""
    try:
        output = subprocess.check_output(
            "ip addr show | grep 'inet ' | awk '{print $2}' | cut -d/ -f1",
            shell=True
        )
        all_ips = output.decode('utf-8').strip().split("\n")
        all_ips = [ip for ip in all_ips if ip and ip != '127.0.0.1']

        priority_ips = []
        other_ips = []

        for ip in all_ips:
            try:
                interface_check = subprocess.check_output(
                    f"ip addr show | grep '{ip}' | head -1", shell=True
                )
                interface_line = interface_check.decode('utf-8').strip()
                if 'tun0' in interface_line or 'eth' in interface_line:
                    priority_ips.append(ip)
                else:
                    other_ips.append(ip)
            except Exception:
                other_ips.append(ip)

        return priority_ips + other_ips if priority_ips + other_ips else ['127.0.0.1']
    except Exception:
        return ['127.0.0.1']


def get_file_type(filepath):
    """Get file MIME type"""
    return mimetypes.guess_type(filepath)[0] or 'application/octet-stream'


def get_file_size(filepath):
    """Get human-readable file size"""
    size_bytes = os.path.getsize(filepath)
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    while size_bytes >= 1024 and unit_index < len(units) - 1:
        size_bytes /= 1024
        unit_index += 1
    return f"{size_bytes:.2f} {units[unit_index]}"


def get_tools_files(tools_folder, ignore_dirs):
    """Get all files in the tools directory with their info"""
    tools_files = []
    for root, dirs, files in os.walk(tools_folder):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, tools_folder)
            tools_files.append(rel_path)
    return tools_files


def get_tools_structure(tools_folder, ignore_dirs):
    """Get structured directory of tools files"""
    structure = {'root': [], 'subdirs': {}}

    # Root directory files
    for item in os.listdir(tools_folder):
        full_path = os.path.join(tools_folder, item)
        if os.path.isfile(full_path) and not item.startswith('.'):
            file_info = {
                'name': item,
                'size': get_file_size(full_path),
                'type': get_file_type(full_path),
                'date': datetime.datetime.fromtimestamp(
                    os.path.getmtime(full_path)
                ).strftime('%d-%m-%Y %H:%M')
            }
            structure['root'].append(file_info)

    # First-level subdirectories
    for item in os.listdir(tools_folder):
        full_path = os.path.join(tools_folder, item)
        if os.path.isdir(full_path) and item not in ignore_dirs:
            structure['subdirs'][item] = []
            for sub_item in os.listdir(full_path):
                sub_full_path = os.path.join(full_path, sub_item)
                if os.path.isfile(sub_full_path) and not sub_item.startswith('.'):
                    file_info = {
                        'name': sub_item,
                        'size': get_file_size(sub_full_path),
                        'type': get_file_type(sub_full_path),
                        'date': datetime.datetime.fromtimestamp(
                            os.path.getmtime(sub_full_path)
                        ).strftime('%d-%m-%Y %H:%M')
                    }
                    structure['subdirs'][item].append(file_info)

    return structure


def get_uploaded_files(upload_folder):
    """Get info about uploaded files"""
    uploaded = []
    metadata = get_upload_metadata(upload_folder)
    for item in os.listdir(upload_folder):
        full_path = os.path.join(upload_folder, item)
        if os.path.isfile(full_path) and not item.startswith('.'):
            file_meta = metadata.get(item, {})
            file_info = {
                'name': item,
                'size': get_file_size(full_path),
                'type': get_file_type(full_path),
                'date': datetime.datetime.fromtimestamp(
                    os.path.getmtime(full_path)
                ).strftime('%d-%m-%Y %H:%M'),
                'source_ip': file_meta.get('source_ip', 'Unknown')
            }
            uploaded.append(file_info)
    return uploaded


def get_upload_metadata(upload_folder):
    """Load upload metadata from JSON file"""
    metadata_file = os.path.join(upload_folder, '.upload_metadata.json')
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_upload_metadata(upload_folder, metadata):
    """Save upload metadata to JSON file"""
    metadata_file = os.path.join(upload_folder, '.upload_metadata.json')
    try:
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    except IOError:
        pass


def extract_basename(filepath):
    """Extract just the filename from a full path (handles both Windows and Unix paths)"""
    if '\\' in filepath:
        filepath = filepath.split('\\')[-1]
    if '/' in filepath:
        filepath = filepath.split('/')[-1]
    return filepath
