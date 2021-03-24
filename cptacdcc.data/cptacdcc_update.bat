@echo off
set VER=%1
if "%VER%" NEQ "" set VER=-%VER%
set URL=http://edwardslab.bmcb.georgetown.edu/software/downloads/CPTAC-DCC
set ZIP=cptacdcc%VER%.win32.zip
cd /d %~dp0
if exist %ZIP% del %ZIP%
wget.exe %URL%/%ZIP%
unzip.exe -o %ZIP% -d ..
cptacdcc.exe --version
if exist %ZIP% del %ZIP%
