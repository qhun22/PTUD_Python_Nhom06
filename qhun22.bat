@echo off
chcp 65001 >nul
title QHUN22 - Quan Ly Server

:: Tao thu muc logs neu chua ton tai
if not exist "logs" mkdir logs

:main_menu
cls
echo ========================================
echo   QHUN22 - Menu Quan Ly
echo ========================================
echo.
echo  [1] Khoi dong Server
echo  [2] Khoi dong Server (Port tuy chon)
echo  [3] Chay Migration
echo  [4] Tao tai khoan Admin
echo  [5] Thu nghiem Gui Email
echo  [6] Xem Log Server
echo  [7] Xoa Log cu
echo  [8] Thoat
echo.
echo ========================================
set /p choice="Chon chuc nang [1-8]: "

if "%choice%"=="1" goto start_server
if "%choice%"=="2" goto start_server_port
if "%choice%"=="3" goto run_migrate
if "%choice%"=="4" goto create_admin
if "%choice%"=="5" goto test_email
if "%choice%"=="6" goto view_log
if "%choice%"=="7" goto clear_log
if "%choice%"=="8" goto exit

echo.
echo [!] Lua chon khong hop le!
timeout /t 2 >nul
goto main_menu


:start_server
cls
echo ========================================
echo   Khoi Dong Server
echo ========================================
echo.
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo [!] Khong the kich hoat Virtual Environment!
    echo    Dam bao thu muc venv ton tai.
    timeout /t 3 >nul
    goto main_menu
)

echo.
echo [i] Dang kiem tra database...
python manage.py migrate --run-syncdb

echo.
echo [OK] Database san sang!
echo.
echo [i] Dang khoi dong server tai http://127.0.0.1:8000/
echo [i] Bam Ctrl+C de dung server
echo.
python manage.py runserver
goto main_menu


:start_server_port
cls
echo ========================================
echo   Khoi Dong Server - Port Tuy Chon
echo ========================================
echo.
set /p port="Nhap port (mac dinh 8000): "
if "%port%"=="" set port=8000

call venv\Scripts\activate.bat

echo.
echo [i] Dang khoi dong server tai http://127.0.0.1:%port%/
echo [i] Bam Ctrl+C de dung server
echo.
python manage.py runserver %port%
goto main_menu


:run_migrate
cls
echo ========================================
echo   Chay Migration
echo ========================================
echo.
call venv\Scripts\activate.bat

echo [i] Dang chay migrations...
python manage.py migrate --run-syncdb

echo.
pause
goto main_menu


:create_admin
cls
echo ========================================
echo   Tao Tai Khoan Admin
echo ========================================
echo.
call venv\Scripts\activate.bat

echo [i] Dang tao tai khoan admin...
python manage.py createsuperuser

echo.
pause
goto main_menu


:test_email
cls
echo ========================================
echo   Thu Nghiem Gui Email
echo ========================================
echo.
echo  [1] Email Dang Ky
echo  [2] Email Quen Mat Khau
echo  [3] Email Xac Thuc Student/Teacher
echo  [0] Quay lai
echo.
set /p email_choice="Chon loai email [0-3]: "

if "%email_choice%"=="0" goto main_menu
if "%email_choice%"=="1" goto test_email_register
if "%email_choice%"=="2" goto test_email_forgot
if "%email_choice%"=="3" goto test_email_student
goto test_email


:test_email_register
echo.
set /p test_email="Nhap dia chi email nhan: "
if "%test_email%"=="" (
    echo [!] Email khong duoc de trong!
    timeout /t 2 >nul
    goto test_email_register
)
call venv\Scripts\activate.bat
python -c "import os, sys, requests, random; otp = str(random.randint(100000, 999999)); api_key = os.getenv('SENDGRID_API_KEY', ''); from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@qhun22.com'); html = '''<div style=\"font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f5f5f5;\"><div style=\"background:#fff;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);\"><h2 style=\"color:#333;text-align:center;\">Xac minh tai khoan QHUN22</h2><p style=\"color:#666;\">Ma OTP cua ban la:</p><div style=\"background:#f0f0f0;padding:15px;text-align:center;font-size:32px;font-weight:bold;letter-spacing:8px;color:#333;\">%%s</div><p style=\"color:#999;font-size:12px;\">Ma co hieu luc trong 5 phut. Vui long khong chia se ma nay cho ai.</p></div></div>''' %% otp; data = {'personalizations': [{'to': [{'email': '%test_email%'}]}], 'from': {'email': from_email}, 'subject': 'Xac minh OTP - QHUN22', 'content': [{'type': 'text/html', 'value': html}]}; r = requests.post('https://api.sendgrid.com/v3/mail/send', json=data, headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'}, timeout=10); print('[OK] Email da gui thanh cong!') if r.status_code in [200, 201, 202] else print('[!] Loi: ' + str(r.status_code))"
echo.
pause
goto main_menu


:test_email_forgot
echo.
set /p test_email="Nhap dia chi email nhan: "
if "%test_email%"=="" (
    echo [!] Email khong duoc de trong!
    timeout /t 2 >nul
    goto test_email_forgot
)
call venv\Scripts\activate.bat
python -c "import os, sys, requests, random; otp = str(random.randint(100000, 999999)); api_key = os.getenv('SENDGRID_API_KEY', ''); from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@qhun22.com'); html = '''<div style=\"font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f5f5f5;\"><div style=\"background:#fff;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);\"><h2 style=\"color:#d9534f;text-align:center;\">Dat Lai Mat Khau QHUN22</h2><p style=\"color:#666;\">Ma OTP cua ban de dat lai mat khau la:</p><div style=\"background:#f0f0f0;padding:15px;text-align:center;font-size:32px;font-weight:bold;letter-spacing:8px;color:#333;\">%%s</div><p style=\"color:#999;font-size:12px;\">Ma co hieu luc trong 5 phut. Neu ban khong yeu cau, vui long bo qua.</p></div></div>''' %% otp; data = {'personalizations': [{'to': [{'email': '%test_email%'}]}], 'from': {'email': from_email}, 'subject': 'OTP Quen Mat Khau - QHUN22', 'content': [{'type': 'text/html', 'value': html}]}; r = requests.post('https://api.sendgrid.com/v3/mail/send', json=data, headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'}, timeout=10); print('[OK] Email da gui thanh cong!') if r.status_code in [200, 201, 202] else print('[!] Loi: ' + str(r.status_code))"
echo.
pause
goto main_menu


:test_email_student
echo.
set /p test_email="Nhap dia chi email nhan: "
if "%test_email%"=="" (
    echo [!] Email khong duoc de trong!
    timeout /t 2 >nul
    goto test_email_student
)
call venv\Scripts\activate.bat
python -c "import os, sys, requests, random; otp = str(random.randint(100000, 999999)); api_key = os.getenv('SENDGRID_API_KEY', ''); from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@qhun22.com'); html = '''<div style=\"font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f5f5f5;\"><div style=\"background:#fff;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);\"><h2 style=\"color:#5bc0de;text-align:center;\">Xac Thuc Student/Teacher - QHUN22</h2><p style=\"color:#666;\">Ma xac thuc cua ban la:</p><div style=\"background:#e8f4fd;padding:15px;text-align:center;font-size:32px;font-weight:bold;letter-spacing:8px;color:#A9CCF0;\">%%s</div><p style=\"color:#999;font-size:12px;\">Ma co hieu luc trong 5 phut. Vui long khong chia se ma nay cho ai.</p></div></div>''' %% otp; data = {'personalizations': [{'to': [{'email': '%test_email%'}]}], 'from': {'email': from_email}, 'subject': 'Ma Xac Thuc Student/Teacher - QHUN22', 'content': [{'type': 'text/html', 'value': html}]}; r = requests.post('https://api.sendgrid.com/v3/mail/send', json=data, headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'}, timeout=10); print('[OK] Email da gui thanh cong!') if r.status_code in [200, 201, 202] else print('[!] Loi: ' + str(r.status_code))"
echo.
pause
goto main_menu


:view_log
cls
echo ========================================
echo   Xem Log Server
echo ========================================
echo.
if not exist "logs\server.log" (
    echo [!] File log khong ton tai!
    timeout /t 2 >nul
    goto main_menu
)

echo [i] Noi dung file log:
echo.
type logs\server.log
echo.
pause
goto main_menu


:clear_log
cls
echo ========================================
echo   Xoa Log
echo ========================================
echo.
if exist "logs\server.log" (
    del logs\server.log
    echo [OK] Da xoa log!
) else (
    echo [!] File log khong ton tai!
)
echo.
timeout /t 2 >nul
goto main_menu


:exit
cls
echo ========================================
echo   Tam Biet!
echo ========================================
echo.
echo [i] Hen gap lai!
echo.
timeout /t 2 >nul
exit
