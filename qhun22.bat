@echo off
chcp 65001 >nul
title QHUN22 - Quản Lý Server

setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PYTHON_EXE="
set "PYTHON_VERSION="
set "PY_MAJOR="
set "PY_MINOR="
set "TARGET_PYTHON_MINOR=10"
set "TARGET_PYTHON_DISPLAY=3.10"
set "IMPORTANT_PKGS=django allauth requests openpyxl dotenv"
set "AI_PKGS=numpy sklearn sentence_transformers faiss fastapi uvicorn pydantic"

:: Tạo thư mục logs nếu chưa tồn tại
if not exist "logs" mkdir logs

:main_menu
cls
echo ========================================
echo   QHUN22 - Menu Quản Lý
echo ========================================
echo.
echo  [0] Cài đặt lần đầu (tạo venv + cài thư viện)
echo  [1] Khởi động Server
echo  [2] Khởi động Server (Port tùy chọn)
echo  [3] Chạy Migration
echo  [4] Tạo tài khoản Admin
echo  [5] Thử nghiệm gửi Email
echo  [6] Xem Log Server
echo  [7] Xóa Log cũ
echo  [8] Xuất requirements.txt từ venv hiện tại
echo  [9] Thoát
echo.
echo ========================================
set /p choice="Chọn chức năng [0-9]: "

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
echo [!] Lựa chọn không hợp lệ!
timeout /t 2 >nul
goto main_menu


:detect_python
py -%TARGET_PYTHON_DISPLAY% --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py -%TARGET_PYTHON_DISPLAY%"
    goto detect_python_version
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto detect_python_version
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py -3"
    goto detect_python_version
)

set "PYTHON_EXE="
goto :eof

:detect_python_version
for /f "tokens=*" %%v in ('%PYTHON_EXE% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2^>nul') do set "PYTHON_VERSION=%%v"
for /f "tokens=*" %%v in ('%PYTHON_EXE% -c "import sys; print(sys.version_info.major)" 2^>nul') do set "PY_MAJOR=%%v"
for /f "tokens=*" %%v in ('%PYTHON_EXE% -c "import sys; print(sys.version_info.minor)" 2^>nul') do set "PY_MINOR=%%v"

if not "%PY_MAJOR%"=="3" (
    set "PYTHON_EXE="
    set "PYTHON_VERSION="
    set "PY_MAJOR="
    set "PY_MINOR="
    goto :eof
)

if not defined PY_MINOR (
    set "PYTHON_EXE="
    set "PYTHON_VERSION="
    set "PY_MAJOR="
    set "PY_MINOR="
    goto :eof
)

if %PY_MINOR% LSS 10 (
    set "PYTHON_EXE="
    set "PYTHON_VERSION="
    set "PY_MAJOR="
    set "PY_MINOR="
)
goto :eof


:activate_venv
if not exist "venv\Scripts\activate.bat" (
    echo [!] Không tìm thấy venv! Hãy chạy [0] Cài đặt lần đầu trước.
    exit /b 1
)
call venv\Scripts\activate.bat >nul 2>&1
if errorlevel 1 (
    echo [!] Không thể kích hoạt Virtual Environment.
    exit /b 1
)
exit /b 0


:verify_package
set "PKG_NAME=%~1"
python -c "import importlib, sys; importlib.import_module('%PKG_NAME%')" >nul 2>&1
if errorlevel 1 (
    echo    [THIẾU] %PKG_NAME%
    set /a MISSING_COUNT+=1
) else (
    echo    [OK] %PKG_NAME%
)
goto :eof


:start_server
cls
echo ========================================
echo   Khởi Động Server
echo ========================================
echo.
call :activate_venv
if errorlevel 1 (
    echo.
    echo [!] Không thể kích hoạt Virtual Environment!
    echo    Đảm bảo thư mục venv tồn tại.
    timeout /t 3 >nul
    goto main_menu
)

echo.
echo [i] Đang kiểm tra database...
python manage.py migrate --run-syncdb

echo.
echo [OK] Database sẵn sàng!
echo.
echo [i] Đang khởi động server tại http://127.0.0.1:8000/
echo [i] Log tổng: logs\server.log
echo [i] Log chatbot: logs\chatbot.log
echo [i] Bấm Ctrl+C để dừng server
echo.
set "DJANGO_LOG_LEVEL=INFO"
set "QH_CHATBOT_LOG_LEVEL=INFO"
powershell -NoProfile -Command "& { python manage.py runserver 2>&1 | Tee-Object -FilePath 'logs\server.log' -Append }"
goto main_menu


:start_server_port
cls
echo ========================================
echo   Khởi Động Server - Port Tùy Chọn
echo ========================================
echo.
set /p port="Nhập port (mặc định 8000): "
if "%port%"=="" set port=8000

call :activate_venv
if errorlevel 1 goto main_menu

echo.
echo [i] Đang khởi động server tại http://127.0.0.1:%port%/
echo [i] Log tổng: logs\server.log
echo [i] Log chatbot: logs\chatbot.log
echo [i] Bấm Ctrl+C để dừng server
echo.
set "DJANGO_LOG_LEVEL=INFO"
set "QH_CHATBOT_LOG_LEVEL=INFO"
powershell -NoProfile -Command "& { python manage.py runserver %port% 2>&1 | Tee-Object -FilePath 'logs\server.log' -Append }"
goto main_menu


:run_migrate
cls
echo ========================================
echo   Chạy Migration
echo ========================================
echo.
call :activate_venv
if errorlevel 1 goto main_menu

echo [i] Đang chạy migrations...
python manage.py migrate --run-syncdb

echo.
pause
goto main_menu


:create_admin
cls
echo ========================================
echo   Tạo Tài Khoản Admin
echo ========================================
echo.
call :activate_venv
if errorlevel 1 goto main_menu

echo [i] Đang tạo tài khoản admin...
python manage.py createsuperuser

echo.
pause
goto main_menu


:test_email
cls
echo ========================================
echo   Thử Nghiệm Gửi Email
echo ========================================
echo.
echo  [1] Email Đăng Ký
echo  [2] Email Quên Mật Khẩu
echo  [3] Email Xác Thực Student/Teacher
echo  [0] Quay lại
echo.
set /p email_choice="Chọn loại email [0-3]: "

if "%email_choice%"=="0" goto main_menu
if "%email_choice%"=="1" goto test_email_register
if "%email_choice%"=="2" goto test_email_forgot
if "%email_choice%"=="3" goto test_email_student
goto test_email


:test_email_register
echo.
set /p test_email="Nhập địa chỉ email nhận: "
if "%test_email%"=="" (
    echo [!] Email không được để trống!
    timeout /t 2 >nul
    goto test_email_register
)
call :activate_venv
if errorlevel 1 goto main_menu
python -c "import os, sys, requests, random; otp = str(random.randint(100000, 999999)); api_key = os.getenv('SENDGRID_API_KEY', ''); from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@qhun22.com'); html = '''<div style=\"font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f5f5f5;\"><div style=\"background:#fff;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);\"><h2 style=\"color:#333;text-align:center;\">Xac minh tai khoan QHUN22</h2><p style=\"color:#666;\">Ma OTP cua ban la:</p><div style=\"background:#f0f0f0;padding:15px;text-align:center;font-size:32px;font-weight:bold;letter-spacing:8px;color:#333;\">%%s</div><p style=\"color:#999;font-size:12px;\">Ma co hieu luc trong 5 phut. Vui long khong chia se ma nay cho ai.</p></div></div>''' %% otp; data = {'personalizations': [{'to': [{'email': '%test_email%'}]}], 'from': {'email': from_email}, 'subject': 'Xac minh OTP - QHUN22', 'content': [{'type': 'text/html', 'value': html}]}; r = requests.post('https://api.sendgrid.com/v3/mail/send', json=data, headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'}, timeout=10); print('[OK] Email da gui thanh cong!') if r.status_code in [200, 201, 202] else print('[!] Loi: ' + str(r.status_code))"
echo.
pause
goto main_menu


:test_email_forgot
echo.
set /p test_email="Nhập địa chỉ email nhận: "
if "%test_email%"=="" (
    echo [!] Email không được để trống!
    timeout /t 2 >nul
    goto test_email_forgot
)
call :activate_venv
if errorlevel 1 goto main_menu
python -c "import os, sys, requests, random; otp = str(random.randint(100000, 999999)); api_key = os.getenv('SENDGRID_API_KEY', ''); from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@qhun22.com'); html = '''<div style=\"font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f5f5f5;\"><div style=\"background:#fff;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);\"><h2 style=\"color:#d9534f;text-align:center;\">Dat Lai Mat Khau QHUN22</h2><p style=\"color:#666;\">Ma OTP cua ban de dat lai mat khau la:</p><div style=\"background:#f0f0f0;padding:15px;text-align:center;font-size:32px;font-weight:bold;letter-spacing:8px;color:#333;\">%%s</div><p style=\"color:#999;font-size:12px;\">Ma co hieu luc trong 5 phut. Neu ban khong yeu cau, vui long bo qua.</p></div></div>''' %% otp; data = {'personalizations': [{'to': [{'email': '%test_email%'}]}], 'from': {'email': from_email}, 'subject': 'OTP Quen Mat Khau - QHUN22', 'content': [{'type': 'text/html', 'value': html}]}; r = requests.post('https://api.sendgrid.com/v3/mail/send', json=data, headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'}, timeout=10); print('[OK] Email da gui thanh cong!') if r.status_code in [200, 201, 202] else print('[!] Loi: ' + str(r.status_code))"
echo.
pause
goto main_menu


:test_email_student
echo.
set /p test_email="Nhập địa chỉ email nhận: "
if "%test_email%"=="" (
    echo [!] Email không được để trống!
    timeout /t 2 >nul
    goto test_email_student
)
call :activate_venv
if errorlevel 1 goto main_menu
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
    echo [!] File log không tồn tại!
    timeout /t 2 >nul
    goto main_menu
)

echo [i] Nội dung file log server:
echo.
type logs\server.log
echo.
if exist "logs\chatbot.log" (
    echo ========================================
    echo [i] Nội dung file log chatbot:
    echo.
    type logs\chatbot.log
)
echo.
pause
goto main_menu


:clear_log
cls
echo ========================================
echo   Xóa Log
echo ========================================
echo.
if exist "logs\server.log" (
    del logs\server.log
    echo [OK] Đã xóa log!
) else (
    echo [!] File log không tồn tại!
)
if exist "logs\chatbot.log" del logs\chatbot.log
echo.
timeout /t 2 >nul
goto main_menu


:setup_install
cls
echo ========================================
echo   Cài Đặt Tự Động - QHUN22
echo ========================================
echo.
echo  Quy trình sẽ tự động chạy, không cần thao tác thêm.
echo  Vui lòng chờ đến khi hoàn tất...
echo.
echo ========================================
echo.

set "MISSING_COUNT=0"

:: ---- BUOC 1: Kiem tra Python ----
echo [1/5] Kiểm tra Python...
call :detect_python
if "%PYTHON_EXE%"=="" (
    echo.
    echo  [THẤT BẠI] Không tìm thấy Python phù hợp!
    echo.
    echo  Vui lòng cài Python 3.10+ từ:
    echo     https://www.python.org/downloads/
    echo.
    echo  Sau khi cài xong, mở lại file bat này và chọn [0].
    echo.
    pause
    goto main_menu
)
for /f "tokens=*" %%v in ('%PYTHON_EXE% --version 2^>^&1') do echo        Phiên bản: %%v
echo  [OK] Python hợp lệ!
if not "%PY_MINOR%"=="%TARGET_PYTHON_MINOR%" (
    echo  [CẢNH BÁO] Máy đang dùng Python %PYTHON_VERSION%.
    echo           Khuyến nghị dùng Python %TARGET_PYTHON_DISPLAY% để ổn định cao nhất giữa các máy.
)
echo.

:: ---- BUOC 2: Tao venv ----
echo [2/5] Tạo Virtual Environment...
if exist "venv\Scripts\activate.bat" (
    echo  [OK] venv đã tồn tại - bỏ qua.
) else (
    %PYTHON_EXE% -m venv venv >nul 2>&1
    if errorlevel 1 (
        echo  [THẤT BẠI] Không thể tạo venv!
        echo             Thử chạy: python -m venv venv
        echo.
        pause
        goto main_menu
    )
    echo  [OK] Đã tạo venv mới.
)
echo.

:: ---- BUOC 3: Kich hoat venv + nang cap pip ----
echo [3/5] Kích hoạt venv và nâng cấp pip...
call :activate_venv
if errorlevel 1 (
    pause
    goto main_menu
)
python -m pip install --upgrade pip setuptools wheel --quiet --disable-pip-version-check --no-warn-script-location
if errorlevel 1 (
    echo  [THẤT BẠI] Không thể cập nhật pip/setuptools/wheel.
    pause
    goto main_menu
)
echo  [OK] pip/setuptools/wheel đã cập nhật.
echo.

:: ---- BƯỚC 4: Cài thư viện ----
echo [4/5] Cài đặt thư viện (core + AI nếu có)...
echo.
if not exist "requirements.txt" (
    echo  [THẤT BẠI] Không tìm thấy requirements.txt
    pause
    goto main_menu
)

pip install -r requirements.txt --disable-pip-version-check --no-warn-script-location
if errorlevel 1 (
    echo.
    echo  [THẤT BẠI] Cài đặt core requirements gặp lỗi!
    echo.
    echo  Nguyên nhân có thể:
    echo    - Không có kết nối Internet
    echo    - requirements.txt bi loi format
    echo.
    echo  Thử kiểm tra kết nối mạng rồi chạy lại [0].
    echo.
    pause
    goto main_menu
)

if exist "ai\ai_requirements.txt" (
    echo.
    echo  [i] Phát hiện ai\ai_requirements.txt - đang cài thêm thư viện AI...
    pip install -r ai\ai_requirements.txt --disable-pip-version-check --no-warn-script-location
    if errorlevel 1 (
        echo.
        echo  [CẢNH BÁO] Cài đặt AI requirements có lỗi.
        echo           Vẫn tiếp tục với core web app.
    ) else (
        echo  [OK] Đã cài đặt xong thư viện AI.
    )
) else (
    echo  [i] Không có ai\ai_requirements.txt - bỏ qua bước thư viện AI.
)

echo.
echo  [i] Kiểm tra nhanh các package quan trọng...
for %%p in (%IMPORTANT_PKGS%) do call :verify_package %%p

if exist "ai\ai_requirements.txt" (
    echo.
    echo  [i] Kiểm tra package AI (nếu thiếu sẽ cảnh báo)...
    for %%p in (%AI_PKGS%) do call :verify_package %%p
)

echo.
if "%MISSING_COUNT%"=="0" (
    echo  [OK] Kiểm tra package hoàn tất - không thiếu thư viện quan trọng.
) else (
    echo  [CẢNH BÁO] Còn %MISSING_COUNT% package chưa import được.
    echo           Nếu lỗi thuộc nhóm AI, app web vẫn có thể chạy bình thường.
)
echo.

:: ---- BUOC 5: Chay migrate ----
echo [5/5] Chạy database migration...
echo.
python manage.py migrate --run-syncdb
if errorlevel 1 (
    echo.
    echo  [CẢNH BÁO] Migration gặp vấn đề - có thể cần cấu hình .env trước.
) else (
    echo.
    echo  [OK] Database sẵn sàng.
)
echo.

:: ---- KIEM TRA FILE .env ----
if not exist ".env" (
    echo ========================================
    echo  CẢNH BÁO: Chưa có file .env
    echo ========================================
    echo.
    echo  Website sẽ KHÔNG chạy được nếu thiếu .env!
    echo  Tạo file .env trong thư mục gốc với nội dung:
    echo.
    echo    SECRET_KEY=your-secret-key
    echo    DEBUG=True
    echo    ALLOWED_HOSTS=127.0.0.1,localhost
    echo    ANTHROPIC_API_KEY=your-api-key
    echo.
    echo  Xem thêm trong README.md
    echo.
) else (
    echo  [OK] File .env đã có sẵn.
    echo.
)

echo ========================================
echo   CÀI ĐẶT HOÀN TẤT!
echo ========================================
echo.
echo   Bước tiếp theo:
echo     - Chọn [1] để khởi động server
echo     - Truy cập: http://127.0.0.1:8000/
echo.
pause
goto main_menu


:export_requirements
cls
echo ========================================
echo   Xuất requirements.txt
echo ========================================
echo.
call :activate_venv
if errorlevel 1 (
    pause
    goto main_menu
)
pip freeze > requirements_freeze.txt
echo [OK] Đã xuất ra file: requirements_freeze.txt
echo     (Đây là snapshot chính xác, dùng để debug xung đột phiên bản)
echo.
pause
goto main_menu


:exit
cls
echo ========================================
echo   Tạm Biệt!
echo ========================================
echo.
echo [i] Hẹn gặp lại!
echo.
timeout /t 2 >nul
exit
