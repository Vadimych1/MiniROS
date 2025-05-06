@ECHO off
echo Adding MiniROS to PATH
SET ppath=%PATH%;%cd%
python3 util/pathadd.py "PATH" "%ppath%"
echo %ppath%
echo Building and installing pip package
cd /d %~dp0
python3 util/build.py
echo Done