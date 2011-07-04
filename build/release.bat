@echo off

set /p version=Enter version number: %=%

"C:\Python27\python.exe" setup.py py2exe

cd dist

upx --best whyteboard.exe

del w9xpopen.exe

cd ..


ren dist "whyteboard-%version%"

"C:\Program Files\7-Zip\7z.exe" a -tzip "whyteboard-%version%.zip" "whyteboard-%version%"

ren "whyteboard-%version%" dist

"C:\Program Files\Inno Setup 5\Compil32.exe"  /cc innosetup.iss

ren Output\setup.exe whyteboard-installer-%version%.exe

move Output\whyteboard-installer-%version%.exe .

rmdir build /S /Q
rmdir dist /S /Q
rmdir Output /S /Q