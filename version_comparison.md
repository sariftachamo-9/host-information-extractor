# Data Extractor Version Comparison

This document analyzes the evolution of the `data_extracter` scripts, showing the progression from a compliance audit tool to a weaponized exfiltration payload.

## Quick Summary

| Feature | v1 (`data_extracter.py`) | v2 (`data_extracter_v2.py`) | v3 (`data_extracter_v3.py`) | v4 (`data_extracter_v4.py`) | v5 (`v5.py`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Purpose** | Educational / Compliance Audit | Portable USB Tool | Automated Exfiltration Payload | Stealth Standalone Executable | Advanced Multi-Module Harvester |
| **Interaction** | **High** (Requires "yes" input) | **Medium** (Menu or Config) | **Zero** (Runs immediately) | **Zero** (Background process) | **Zero** (Background process/console) |
| **Scope** | Single hardcoded folder | Single configurable drive | **All** detected drives & User folders | **All** connected drives (except self) | **All** drives, User folders, Browsers, Registry, & System info |
| **Stealth** | None (Prints everything) | Optional "Stealth Mode" | Silent Progress / Log file | **High** (Silent GUI-less executable) | **High** (Silent run, hidden autorun, error silencing) |
| **Output** | Flat folder | Flat folder | **Categorized** (financial, keys, etc.) | **Categorized** with timestamped names | Highly structured folders, detailed JSON report, CSV index, system/network logs, registry, and browser exports |
| **Capabilities**| Basic file copy | Self-aware USB drive letter detection | Drive discovery & System path exclusion | PyInstaller build script for compilation | Credential harvesting (WiFi, Browsers), Registry dump, & Deep regex-based content analysis |

---

## Detailed Analysis

### Version 1: The "Polite" Auditor
**Filename:** `data_extracter.py`

*   **Logic:** A safe, educational script.
*   **Safety Catch:** It refuses to run unless the user manually types "yes" to an authorization prompt.
*   **Targeting:** Looks only at `D:\CyberLab\SensitiveMock`.
*   **Use Case:** verifying if a specific folder contains sensitive data.

### Version 2: The "Swiss Army Knife"
**Filename:** `data_extracter_v2.py`

*   **Logic:** Designed to be carried on a USB stick.
*   **Self-Awareness:** Detects its own drive letter to ensure data is saved back to the USB drive, regardless of which computer it's plugged into.
*   **Configuration:** Uses a `config.json` file. You can configure it to be "stealthy" (hide text) or "interactive" (show a menu).
*   **Legacy Attack:** Includes code to generate an `autorun.inf` file (an older method of triggering execution).

### Version 3: The "Weaponized" Script
**Filename:** `data_extracter_v3.py`

*   **Logic:** Aggressive automation. The moment it runs, it starts working.
*   **No Hand-Holding:** Removed all "Are you sure?" prompts and menus.
*   **Mass Scope:**
    *   Scans **ALL** connected hard drives (C:, D:, E:, etc.).
    *   Specifically targets user profile folders (Desktop, Documents, OneDrive).
*   **Smart Sort:** Instead of a messy pile of files, it organizes stolen data:
    *   `/success/financial/`
    *   `/success/credentials/`
    *   `/success/databases/`
*   **Evasion:** Skips system folders (`Windows`, `Program Files`) to avoid wasting time and detection. Auto-exits when done.

### Version 4: The "Invisible" Executable
**Filename:** `v4/data_extracter_v4.py` (Compiled to `USB_Audit_Tool.exe`)

*   **Logic:** Focuses on packaging and binary concealment.
*   **Compilation:** Includes a batch script `build_exe.bat` that uses PyInstaller to compile the script into a standalone `.exe` using the `--noconsole` and `--onefile` flags. This prevents any terminal/command prompt window from showing when the tool runs.
*   **Execution Safeguard:** Specifically queries and lists all connected logical drives except the drive letter where the executable is running (to avoid scanning its own output directory and creating a loop).
*   **Targeting:** Refines search parameters with specific regex categories (`credentials`, `personal`, `financial`, `documents`) and target extensions.
*   **Stealth:** Suppresses all output to the screen, has a 3-second startup sleep, and uses try-except blocks to fail silently on read/access errors.

### Version 5: The "All-in-One" Harvester
**Filename:** `v5/v5.py`

*   **Logic:** A full-featured post-exploitation information stealer and intelligence gathering payload.
*   **Modules:**
    *   **Browser Stealer:** Locates Chrome, Edge, Firefox, Brave, and Opera user profile directories. Specifically targets and copies browser databases containing logins, cookies, history, bookmarks, and web data.
    *   **Credential/Network Harvesting:** Queries Windows shell via `netsh wlan show profiles` to pull wifi profiles and retrieve cleartext passwords. Also grabs active network configurations like `hosts` and `networks` files.
    *   **Registry Dumper:** Connects to the Windows registry to dump specific keys like startup paths (`Run`), user search history (`RunMRU`), recent documents (`RecentDocs`), and network configurations.
    *   **System Profiler:** Gathers comprehensive hostname, IP, username, and environmental profiles.
    *   **Deep Content Analysis:** Scans the first 50KB of files looking for structured strings such as credit card numbers, email addresses, IP addresses, URLs, and API keys.
*   **Evasion & Persistence:** Generates a hidden, system-marked `autorun.inf` to auto-trigger the execution of the payload when the USB is plugged in on older or vulnerable systems.
*   **Reporting:** Output is highly organized into categorized folders under `Extracted_Data/`. Generates a full audit trail via a detailed `extraction_report.json` and a spreadsheet summary `extracted_files.csv`.
