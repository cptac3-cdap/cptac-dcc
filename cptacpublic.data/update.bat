@echo off
set VER=%1
if "%VER%" NEQ "" set VER=-%VER%
set URL=http://cptac-cdap.georgetown.edu.s3-website-us-east-1.amazonaws.com
set ZIP=cptacpublic%VER%.win32.zip
cd /d %~dp0
if exist %ZIP% del %ZIP%
wget.exe %URL%/%ZIP%
unzip.exe -o %ZIP% -d ..
cptacpublic.exe --version
if exist %ZIP% del %ZIP%
