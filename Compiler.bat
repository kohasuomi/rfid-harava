@echo off
rem Build the executables using PyInstaller
py -m PyInstaller --onefile --windowed --icon=harava.png --name RfidHarava main.py

rem Set the release directory name
set RELEASE_DIR=Release

rem Create the release directory and its subdirectory if they don't exist
if not exist %RELEASE_DIR% mkdir %RELEASE_DIR%
if not exist %RELEASE_DIR%\RfidHarava mkdir %RELEASE_DIR%\RfidHarava

rem Copy the built executables to the release directory
copy dist\RfidHarava.exe %RELEASE_DIR%\RfidHarava\
copy harava.png %RELEASE_DIR%\RfidHarava\

rem Config folder
if not exist %RELEASE_DIR%\RfidHarava\Configs mkdir %RELEASE_DIR%\RfidHarava\Configs
copy Configs\config.ini %RELEASE_DIR%\RfidHarava\Configs
copy Configs\ConfigBase.ini %RELEASE_DIR%\RfidHarava\Configs\config.ini
copy Configs\UserSettingsBase.ini %RELEASE_DIR%\RfidHarava\Configs\UserSettings.ini

rem Create and copy the GUI folder (including stylesheet and any other files/subdirs)
if not exist %RELEASE_DIR%\RfidHarava\GUI mkdir %RELEASE_DIR%\RfidHarava\GUI
copy GUI\theme.css %RELEASE_DIR%\RfidHarava\GUI 

rem Create and copy the resources folder (including sound effects and any other files/subdirs)
if not exist %RELEASE_DIR%\RfidHarava\resources mkdir %RELEASE_DIR%\RfidHarava\resources
xcopy resources %RELEASE_DIR%\RfidHarava\resources /s /i /y /q

if not exist %RELEASE_DIR%\Ohjeet mkdir %RELEASE_DIR%\Ohjeet
xcopy Ohjeet %RELEASE_DIR%\Ohjeet /s /i /y /q

if not exist %RELEASE_DIR%\RfidHarava\logs mkdir %RELEASE_DIR%\RfidHarava\logs

if not exist %RELEASE_DIR%\RfidHarava\Lists mkdir %RELEASE_DIR%\RfidHarava\Lists

pause