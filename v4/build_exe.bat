@echo off
echo [*] Building USB Audit Tool (v4)...
echo.

rem Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] PyInstaller not found. Installing...
    pip install pyinstaller
)

echo [*] Compiling to standalone EXE...
pyinstaller --noconsole --onefile --name "USB_Audit_Tool" "data_extracter_v4.py"

echo.
echo [V] Build Complete!
echo [!] COPY 'dist\USB_Audit_Tool.exe' TO YOUR USB DRIVE.
echo.
pause
