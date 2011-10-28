@echo off

rmdir build /S /Q
rmdir dist /S /Q

"C:\Python27\python.exe" setup.py py2exe