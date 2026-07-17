Set WshShell = CreateObject("WScript.Shell")
strPath = WshShell.CurrentDirectory & "\data_extracter.py"

' The script requires user input for authorization, so we must run it visible (1)
' usage: Run "command", window_style, wait_on_return
WshShell.Run "python """ & strPath & """", 1, True
