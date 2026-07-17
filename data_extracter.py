import os
import shutil
import hashlib
import json
import re
from datetime import datetime
import time

# Configuration - THESE SHOULD BE CONFIGURED WITH PROPER AUTHORIZATION
LAB_SOURCE = r"D:\CyberLab\SensitiveMock"  # Training directory
LAB_OUTPUT = r"D:\CyberLab\AuditResults"   # Authorized audit location
LOG_FILE = r"D:\CyberLab\audit_log.json"

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

def scan_directory_for_sensitive(directory, max_depth=3):
    """Recursively scan directory for potentially sensitive files"""
    sensitive_files = []
    
    for root, dirs, files in os.walk(directory):
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

def automated_scan_and_collect():
    """Automated scan and collection with logging"""
    print("=" * 70)
    print("AUTOMATED SENSITIVE DATA AUDIT TOOL")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Source: {LAB_SOURCE}")
    print(f"Output: {LAB_OUTPUT}")
    print("=" * 70)
    
    # Create output directory
    os.makedirs(LAB_OUTPUT, exist_ok=True)
    
    # Scan for sensitive files
    print("\n🔍 Scanning for potentially sensitive files...")
    start_time = time.time()
    
    sensitive_files = scan_directory_for_sensitive(LAB_SOURCE)
    
    scan_time = time.time() - start_time
    
    print(f"📊 Scan completed in {scan_time:.2f} seconds")
    print(f"📈 Found {len(sensitive_files)} potentially sensitive files")
    
    if not sensitive_files:
        print("✅ No sensitive files found.")
        return
    
    # Display scan summary
    print("\n📋 SENSITIVITY CATEGORIES FOUND:")
    categories = {}
    for file_info in sensitive_files:
        cat = file_info['sensitivity_reason']
        categories[cat] = categories.get(cat, 0) + 1
    
    for category, count in categories.items():
        print(f"  {category}: {count} files")
    
    # Create detailed report
    report = {
        'audit_timestamp': datetime.now().isoformat(),
        'source_directory': LAB_SOURCE,
        'output_directory': LAB_OUTPUT,
        'total_files_scanned': 'N/A',  # Would need to count all files
        'sensitive_files_found': len(sensitive_files),
        'categories': categories,
        'files': sensitive_files
    }
    
    # Save report
    with open(os.path.join(LAB_OUTPUT, 'audit_report.json'), 'w') as f:
        json.dump(report, f, indent=2)
    
    # Copy files (for audit/analysis purposes with proper authorization)
    print("\n📁 Copying files for analysis...")
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
                print(f"✅ Copied: {filename} -> {unique_name}")
            else:
                error_count += 1
                
        except Exception as e:
            error_count += 1
            print(f"❌ Error copying {file_info['filename']}: {str(e)}")
    
    # Create summary log
    summary = {
        'timestamp': datetime.now().isoformat(),
        'operation': 'automated_sensitive_data_audit',
        'source': LAB_SOURCE,
        'destination': LAB_OUTPUT,
        'files_found': len(sensitive_files),
        'files_copied': copied_count,
        'errors': error_count,
        'scan_duration_seconds': scan_time
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
    
    print("\n" + "=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)
    print(f"📊 Files identified as potentially sensitive: {len(sensitive_files)}")
    print(f"📁 Successfully copied: {copied_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📄 Report saved to: {os.path.join(LAB_OUTPUT, 'audit_report.json')}")
    print(f"📋 Log entry added to: {LOG_FILE}")
    print("=" * 70)

def integrity_check():
    """Verify integrity of collected files"""
    print("\n🔍 Verifying collected files integrity...")
    
    if not os.path.exists(LAB_OUTPUT):
        print("❌ Output directory doesn't exist!")
        return
    
    # Look for the audit report
    report_path = os.path.join(LAB_OUTPUT, 'audit_report.json')
    
    if not os.path.exists(report_path):
        print("❌ No audit report found!")
        return
    
    with open(report_path, 'r') as f:
        report = json.load(f)
    
    print(f"📋 Audit from: {report['audit_timestamp']}")
    print(f"📁 Files in report: {len(report['files'])}")
    
    verified = 0
    missing = 0
    hash_mismatch = 0
    
    for file_info in report['files']:
        expected_hash = file_info['hash']
        filename = file_info['filename']
        
        # Find the copied file (with timestamp suffix)
        copied_files = [f for f in os.listdir(LAB_OUTPUT) 
                       if f.startswith(filename.split('.')[0])]
        
        if not copied_files:
            print(f"❌ Missing: {filename}")
            missing += 1
            continue
        
        # Check each matching file
        for copied_file in copied_files:
            copied_path = os.path.join(LAB_OUTPUT, copied_file)
            actual_hash = file_hash(copied_path)
            
            if actual_hash == expected_hash:
                print(f"✅ Verified: {filename} -> {copied_file}")
                verified += 1
                break
            else:
                print(f"⚠️ Hash mismatch: {filename}")
                hash_mismatch += 1
    
    print(f"\n📊 Integrity Check Summary:")
    print(f"✅ Verified: {verified}")
    print(f"❌ Missing: {missing}")
    print(f"⚠️ Hash mismatches: {hash_mismatch}")

def main():
    """Main function with disclaimer"""
    print("⚠️  DISCLAIMER: This tool is for EDUCATIONAL PURPOSES ONLY")
    print("⚠️  Use only on systems you own or have EXPLICIT AUTHORIZATION to audit")
    print("⚠️  Unauthorized scanning/copying of data may be ILLEGAL\n")
    
    # Check authorization (simulated - in real use, this would be proper authentication)
    print("=" * 70)
    print("AUTHORIZATION CHECK")
    print("=" * 70)
    
    # In a real scenario, you would have proper authentication here
    # For this educational example, we'll simulate with a prompt
    response = input("Do you have proper authorization to run this audit? (yes/no): ").lower()
    
    if response != 'yes':
        print("\n❌ Audit cancelled. Proper authorization is required.")
        return
    
    print("\n✅ Authorization confirmed. Starting automated audit...")
    
    # Run automated scan
    automated_scan_and_collect()
    
    # Option to verify
    verify = input("\nRun integrity check on collected files? (yes/no): ").lower()
    if verify == 'yes':
        integrity_check()
    
    print("\n" + "=" * 70)
    print("AUDIT PROCESS COMPLETE")
    print("=" * 70)
    print("📁 Files available in:", LAB_OUTPUT)
    print("📋 Log file:", LOG_FILE)
    print("⏰ Completed at:", datetime.now().isoformat())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Audit interrupted by user.")
    except Exception as e:
        print(f"\n❌ Error during audit: {str(e)}")
    finally:
        input("\nPress Enter to exit...")