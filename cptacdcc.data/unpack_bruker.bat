
@echo off

REM    Check checksums and unpack Bruker MS data
REM    Assumes the following structure:
REM
REM    01AS/
REM       01AS_F1.d.zip
REM       01AS_F2.d.zip
REM       01AS_F3.d.zip
REM    01AS.cksum
REM    02AS/
REM       02AS_F1.d.zip
REM       02AS_F2.d.zip
REM       02AS_F3.d.zip
REM    02AS.cksum
REM
REM    Should be run from the folder with the analytical sample directories (01AS, 02AS)
REM
REM

echo|(set /p="> cksum -q -V *.cksum" & echo.)
%~dp0cksum -q -V *.cksum
if %ERRORLEVEL% NEQ 0 GOTO :BADCKSUM

echo|(set /p="> unpackraw -r d -R -v" & echo.)
%~dp0unpackraw -r d -R -v
GOTO :EOF

:BADCKSUM
echo|(set /p="Bad checksum! Will not unpack Bruker files." & echo.)

:EOF