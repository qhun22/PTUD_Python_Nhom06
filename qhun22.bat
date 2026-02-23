@echo off
echo ========================================
echo   QHUN22 Mobile - Khoi Dong Server
echo ========================================
echo.

REM Kich hoach virtual environment
call venv\Scripts\activate.bat

REM Chay migrations (neu can)
echo Dang kiem tra database...
python manage.py migrate --run-syncdb

REM Khoi dong server
echo.
echo Dang khoi dong server...
python manage.py runserver

REM Giu cua so terminal
pause
