
@echo off

REM    Package and compute checksums for Bruker MS data
REM    Assumes the following structure:
REM
REM    01AS/
REM       01AS_F1.d/
REM          ...
REM       01AS_F2.d/
REM          ...
REM       01AS_F3.d/
REM          ...
REM    02AS/
REM       02AS_F1.d/
REM          ...
REM       02AS_F2.d/
REM          ...
REM       02AS_F3.d/
REM          ...
REM
REM    Should be run from the folder with the analytical sample directories (01AS, 02AS)
REM
REM

echo|(set /p="> rmdir /s /q packaged" & echo.)
rmdir /s /q packaged
echo|(set /p="> packageraw -r d -d packaged -v" & echo.)
%~dp0packageraw -r d -d packaged -v
echo|(set /p="> cksum packaged\*" & echo.)
%~dp0cksum packaged\*

