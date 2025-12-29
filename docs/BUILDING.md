# Building ComputerManager

This guide covers how to build the ComputerManager application for Windows, Linux, and macOS.

## Prerequisites

- Python 3.10 or higher
- `pip` package manager
- Virtual environment (recommended)

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. This will install PyInstaller and `icnsutil` which are required for the build process.

## Build Process

The project includes automated build scripts for each platform that handle:
1. Icon conversion (ICNS → ICO/PNG)
2. PyInstaller packaging
3. Asset bundling

### Windows

Run the batch script:
```batch
build\build_windows.bat
```
Output: `dist\ComputerManager.exe`

### Linux

Run the shell script:
```bash
./build/build_linux.sh
```
Output: `dist/ComputerManager`

### macOS

Run the shell script:
```bash
./build/build_macos.sh
```
Output: `dist/ComputerManager.app`

## Spec File Configuration

The build uses platform-specific spec files in the `build/` directory:

- **Windows (`build_windows.spec`)**: Configured for one-file mode (`.exe`), includes `assets/`, handles hidden imports for PyQt6, ollama, and automation tools. Uses `icon.ico`.
- **Linux (`build_linux.spec`)**: Configured for one-file mode binary, console optional (can be changed in spec). Uses `icon.png`. Excluding UPX compression for compatibility.
- **macOS (`build_macos.spec`)**: Configured for `BUNDLE` mode to create a `.app` package. Uses `icon.icns`.

## Icon Management

The primary icon source is `assets/icon.icns`.
The build process automatically converts this to:
- `assets/icon.ico` (Windows)
- `assets/icon.png` (Linux)

This is handled by `build/convert_icons.py`.

## Troubleshooting

### Missing Modules
If the executable fails to run due to `ModuleNotFoundError`, add the missing module to the `hiddenimports` list in the corresponding `.spec` file.

### Icon Issues
If icon conversion fails:
1. Ensure `icnsutil` is installed.
2. The script will attempt to fallback to Pillow if available.
3. Verify `assets/icon.icns` exists and is valid.

### Platform Specifics
- **Windows**: Antivirus might flag unsigned one-file executables. This is normal for PyInstaller.
- **macOS**: The `.app` bundle is not code-signed by default. You may need to sign it for distribution or allow it in Security settings.
- **Linux**: Ensure the output binary has executable permissions (`chmod +x`).
