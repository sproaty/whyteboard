@echo off

IF "%1"=="" (set /p version=Enter version number: %=%) ELSE ( set version=%1)

call binaries.bat

"C:\Python27\python.exe" write-latest-update-file.py %version% windows
"C:\Python27\python.exe" upload-latest-update-file.py