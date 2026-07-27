@echo off
setlocal

set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
python -m unittest discover -s "%~dp0tests" -v

exit /b %ERRORLEVEL%
