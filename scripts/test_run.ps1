$ErrorActionPreference = "Stop"

$source = Get-Location
$dest = "$env:TEMP\ComputerManager_TestRun"

Write-Host "=== Starting Isolated Test Run ==="
Write-Host "Source: $source"
Write-Host "Destination: $dest"

# 1. Cleanup
if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Path $dest | Out-Null
}

# 2. Copy Files
Write-Host "Copying project files..."
$exclude = @('.git', 'venv', '__pycache__', 'build', 'dist', 'artifacts', '.vscode', 'temp_test_run', 'node_modules')

# Get top-level items and copy them recursively, excluding the ignored folders
Get-ChildItem -Path $source | Where-Object { $exclude -notcontains $_.Name } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $dest -Recurse -Force
}

# 3. Setup Environment
Set-Location $dest
if (-not (Test-Path "venv")) {
    Write-Host "Setting up virtual environment in $dest..."
    python -m venv venv
    
    # Activate venv
    $venvKey = "venv\Scripts\Activate.ps1"
    if (Test-Path $venvKey) {
        . $venvKey
    }
    
    # 4. Install Dependencies
    Write-Host "Installing dependencies..."
    python -m pip install --upgrade pip
    pip install -r requirements.txt
}
else {
    Write-Host "Using existing virtual environment..."
    $venvKey = "venv\Scripts\Activate.ps1"
    if (Test-Path $venvKey) {
        . $venvKey
    }
}

# 5. Run Application
Write-Host "Running application..."
$env:PYTHONPATH = $dest
try {
    # Run a quick check first to catch import errors without launching the full GUI if possible,
    # or just run main.py and hope it stays up long enough to log errors.
    # We will try to import main and see if it crashes immediately.
    python -c "import sys; print('Python executable:', sys.executable); import src.main; print('Module src.main imported successfully')"
}
catch {
    Write-Error "Failed during execution: $_"
}

Write-Host "=== Test Run Complete ==="
