@echo off

rd build /S /Q
rd dist /S /Q

pushd ..\

"C:\Python27\python.exe" setup.py py2exe

popd