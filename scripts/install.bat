@ECHO off
@REM echo Adding MiniROS to PATH
@REM SET ppath=%PATH%;%cd%
@REM python3 util/pathadd.py "PATH" "%ppath%"

echo Building and installing pip package
if %errorlevel%==0 ( cd . ) else ( echo Build failed && exit )
cd /d %~dp0
if %errorlevel%==0 ( cd . ) else ( echo Build failed && exit )
cd ..
if %errorlevel%==0 ( cd . ) else ( echo Build failed && exit )
python util/build.py %*

if %errorlevel%==0 ( echo Build done && exit ) else ( echo Build failed && exit )