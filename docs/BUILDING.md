# Building Computer Manager

This document provides instructions for building the Computer Manager application from source.

## Prerequisites

- Python 3.11 or higher
- PyInstaller (`pip install pyinstaller`)
- Platform-specific dependencies:
  - **Windows**: Visual C++ Redistributable (usually present)
  - **Linux**: `python3-tk`, `python3-dev`, `libxcb-xinerama0`
  - **macOS**: Xcode Command Line Tools

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/computer-manager.git
   cd computer-manager
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

## Building Locally

### Windows

Run the build script:
```batch
build\build_windows.bat
```
The executable will be located at `build\dist\ComputerManager.exe`.

### Linux

Run the build script:
```bash
./build/build_linux.sh
```
The executable will be located at `build/dist/ComputerManager`.

### macOS

Run the build script:
```bash
./build/build_macos.sh
```
The application bundle will be located at `build/dist/ComputerManager.app`.

## Troubleshooting

### Windows
- If you encounter DLL errors, ensure the Visual C++ Redistributable is installed.
- "Windows protected your PC" warning is normal for unsigned executables.

### Linux
- If the build fails with missing library errors, ensure you have installed the required system packages (see Prerequisites).
- If the app doesn't launch, try running it from the terminal to see error output.

### macOS
- If the app is "damaged" or can't be opened, you may need to strip the quarantine attribute:
  ```bash
  xattr -cr dist/ComputerManager.app
  ```

## Optimization

The build specifications use sensible defaults to balance size and functionality:
- `UPX` compression is enabled for Windows and macOS (disable if antivirus flags it false positive).
- Unused modules (tkinter, matplotlib, numpy) are explicitly excluded.

## Distribution

This project uses GitHub Actions for automated builds on fresh tags. See `.github/workflows/build-release.yml` for details.
