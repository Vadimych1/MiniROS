@ECHO off
@REM echo Adding MiniROS to PATH
@REM SET ppath=%PATH%;%cd%
@REM python3 util/pathadd.py "PATH" "%ppath%"
echo Building and installing pip package
cd /d %~dp0
python3 util/build.py
echo Done