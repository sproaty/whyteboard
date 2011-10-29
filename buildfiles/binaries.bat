@echo off

set _=%CD%\

IF "%1"=="" (set /p version=Enter version number: %=%) ELSE ( set version=%1)

pushd %_%\
pushd scripts

"C:\Python27\python.exe" update-version.py %version%

popd
call build.bat

pushd ..\dist

upx --best whyteboard.exe

del w9xpopen.exe

popd
pushd ..

ren dist "whyteboard-%version%"

"C:\Program Files\7-Zip\7z.exe" a -tzip "whyteboard-%version%.zip" "whyteboard-%version%"

ren "whyteboard-%version%" dist

"C:\Program Files\Inno Setup 5\Compil32.exe"  /cc buildfiles\resources\innosetup.iss

echo. 
echo renaming files
echo.

ren buildfiles\resources\Output\setup.exe whyteboard-installer-%version%.exe

echo moving files to build files folder

move buildfiles\resources\Output\whyteboard-installer-%version%.exe buildfiles
move whyteboard-%version%.zip buildfiles

echo cleaning temp. files
rmdir build /S /Q
rmdir dist /S /Q
rmdir buildfiles\resources\Output /S /Q

popd
popd