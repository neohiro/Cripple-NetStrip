$ErrorActionPreference = "Stop"

# Get CustomTkinter path
Write-Host "Locating CustomTkinter..."
$ctk_path = (python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))")
if (-not $ctk_path) {
    Write-Error "Could not find CustomTkinter path. Is it installed?"
}

Write-Host "CustomTkinter found at: $ctk_path"

# Define the PyInstaller command
$args = @(
    "--noconfirm",
    "--onefile",
    "--noconsole",
    "--windowed",
    "--name", "NetStrip",
    "--icon", "assets/logo.ico",
    "--add-data", "$ctk_path;customtkinter/",
    "--add-data", "netstrip/data;netstrip/data/",
    "--add-data", "assets;assets/",
    "--hidden-import", "PIL._tkinter_finder",
    "main.py"
)

Write-Host "Running PyInstaller..."
# Execute PyInstaller
pyinstaller $args

Write-Host "Build complete! Standalone executable is in the 'dist' folder."
