@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   Building Aieator - Motion Graphics Compositor
echo ===================================================

:: 1. Compile Windows resource file (icons)
echo [1/3] Compiling Windows resource file (app_res.rc)...
windres app_res.rc -O coff -o app_res.res
if %errorlevel% neq 0 (
    echo [ERROR] Failed to compile resources with windres.
    exit /b %errorlevel%
)

:: 2. Check if main.cpp exists, or if gen.py should be run
if not exist "main.cpp" (
    echo [2/3] main.cpp not found. Generating from gen.py...
    python gen.py
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to generate main.cpp from gen.py.
        exit /b %errorlevel%
    )
) else (
    echo [2/3] main.cpp found. Proceeding with compilation...
)

:: 3. Compile standalone C++ executable with g++
echo [3/3] Compiling aieator.exe with MinGW g++ (C++17, -O3)...
g++ -O3 -std=c++17 main.cpp app_res.res ^
    thirdparty/imgui/imgui.cpp ^
    thirdparty/imgui/imgui_draw.cpp ^
    thirdparty/imgui/imgui_widgets.cpp ^
    thirdparty/imgui/imgui_tables.cpp ^
    thirdparty/imgui/backends/imgui_impl_win32.cpp ^
    thirdparty/imgui/backends/imgui_impl_opengl3.cpp ^
    -o aieator.exe -mwindows ^
    -Ithirdparty -Ithirdparty/imgui -Ithirdparty/imgui/backends ^
    -lopengl32 -lgdi32 -luser32 -lkernel32 -lcomdlg32 -lshell32 -ldwmapi ^
    -lole32 -loleaut32 -luuid -lmfplat -lmfreadwrite -lmfuuid -lwinmm

if %errorlevel% neq 0 (
    echo [ERROR] Compilation failed.
    exit /b %errorlevel%
)

echo.
echo ===================================================
echo   Build Successful: aieator.exe (~3MB standalone)
echo ===================================================
