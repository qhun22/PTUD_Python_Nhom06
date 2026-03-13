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
echo  [0] Cai dat lan dau (tao venv + cai thu vien)
echo  [1] Khoi dong Server
echo  [2] Khoi dong Server (Port tuy chon)
echo  [3] Chay Migration
echo  [4] Tao tai khoan Admin
echo  [5] Thu nghiem Gui Email
echo  [6] Xem Log Server
echo  [7] Xoa Log cu
echo  [8] Xuat requirements.txt tu venv hien tai
echo  [9] Thoat
echo.
echo ========================================
set /p choice="Chon chuc nang [0-9]: "

if "%choice%"=="0" goto setup_install
if "%choice%"=="1" goto start_server
if "%choice%"=="2" goto start_server_port
if "%choice%"=="3" goto run_migrate
if "%choice%"=="4" goto create_admin
if "%choice%"=="5" goto test_email
if "%choice%"=="6" goto view_log
if "%choice%"=="7" goto clear_log
if "%choice%"=="8" goto export_requirements
if "%choice%"=="9" goto exit

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


:setup_install
cls
echo ========================================
echo   Cai Dat Tu Dong - QHUN22
echo ========================================
echo.
echo  Quy trinh se tu dong chay khong can thao tac them.
echo  Vui long cho den khi hoan tat...
echo.
echo ========================================
echo.

:: ---- BUOC 1: Kiem tra Python ----
echo [1/5] Kiem tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [THAT BAI] Khong tim thay Python!
    echo.
    echo  Vui long cai Python 3.10+ tu:
    echo     https://www.python.org/downloads/
    echo.
    echo  Sau khi cai xong, mo lai file bat nay va chon [0].
    echo.
    pause
    goto main_menu
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo        Phien ban: %%v
echo  [OK] Python hop le!
echo.

:: ---- BUOC 2: Tao venv ----
echo [2/5] Tao Virtual Environment...
if exist "venv\Scripts\activate.bat" (
    echo  [OK] venv da ton tai - bo qua.
) else (
    python -m venv venv >nul 2>&1
    if errorlevel 1 (
        echo  [THAT BAI] Khong the tao venv!
        echo             Thu chay: python -m venv venv
        echo.
        pause
        goto main_menu
    )
    echo  [OK] Da tao venv moi.
)
echo.

:: ---- BUOC 3: Kich hoat venv + nang cap pip ----
echo [3/5] Kich hoat venv va nang cap pip...
call venv\Scripts\activate.bat >nul 2>&1
python -m pip install --upgrade pip --quiet --no-warn-script-location
echo  [OK] pip da cap nhat.
echo.

:: ---- BUOC 4: Cai thu vien ----
echo [4/5] Cai dat thu vien tu requirements.txt...
echo.
pip install -r requirements.txt --no-warn-script-location
if errorlevel 1 (
    echo.
    echo  [THAT BAI] Cai dat thu vien gap loi!
    echo.
    echo  Nguyen nhan co the:
    echo    - Khong co ket noi Internet
    echo    - requirements.txt bi loi format
    echo.
    echo  Thu kiem tra ket noi mang roi chay lai [0].
    echo.
    pause
    goto main_menu
)
echo.
echo  [OK] Tat ca thu vien da duoc cai dat.
echo.

:: ---- BUOC 5: Chay migrate ----
echo [5/5] Chay database migration...
echo.
python manage.py migrate --run-syncdb
if errorlevel 1 (
    echo.
    echo  [CANH BAO] Migration gap van de - co the can cau hinh .env truoc.
) else (
    echo.
    echo  [OK] Database san sang.
)
echo.

:: ---- KIEM TRA FILE .env ----
if not exist ".env" (
    echo ========================================
    echo  CANH BAO: Chua co file .env
    echo ========================================
    echo.
    echo  Website se KHONG chay duoc neu thieu .env!
    echo  Tao file .env trong thu muc goc voi noi dung:
    echo.
    echo    SECRET_KEY=your-secret-key
    echo    DEBUG=True
    echo    ALLOWED_HOSTS=127.0.0.1,localhost
    echo    ANTHROPIC_API_KEY=your-api-key
    echo.
    echo  Xem them trong README.md
    echo.
) else (
    echo  [OK] File .env da co san.
    echo.
)

echo ========================================
echo   CAI DAT HOAN TAT!
echo ========================================
echo.
echo   Buoc tiep theo:
echo     - Chon [1] de khoi dong server
echo     - Truy cap: http://127.0.0.1:8000/
echo.
pause
goto main_menu


:export_requirements
cls
echo ========================================
echo   Xuat requirements.txt
echo ========================================
echo.
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [!] Khong tim thay venv! Hay chay [0] Cai dat lan dau truoc.
    pause
    goto main_menu
)
pip freeze > requirements_freeze.txt
echo [OK] Da xuat ra file: requirements_freeze.txt
echo     (Day la snapshot chinh xac, dung de debug version conflict)
echo.
pause
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
