# Automation Tools Documentation

This document provides detailed information about all automation tools available in Computer Manager.

## Table of Contents

- [File Operations](#file-operations)
- [Process Management](#process-management)
- [Web Browsing](#web-browsing)
- [Screen Capture](#screen-capture)
- [Keyboard & Mouse Control](#keyboard--mouse-control)
- [Security Considerations](#security-considerations)
- [Platform-Specific Notes](#platform-specific-notes)
- [Example Usage](#example-usage)

## File Operations

### read_file

Read the contents of a file.

**Parameters:**
- `path` (string, required): Path to the file to read (absolute or relative)
- `encoding` (string, optional): File encoding (default: utf-8)

**Returns:** File content as string or error message

**Example:**
```json
{
  "name": "read_file",
  "parameters": {
    "path": "C:\\Users\\Documents\\notes.txt"
  }
}
```

**Error Handling:**
- FileNotFoundError: File doesn't exist
- PermissionError: No read access
- UnicodeDecodeError: Invalid encoding

---

### write_file

Write or append content to a file. Creates parent directories if needed.

**Parameters:**
- `path` (string, required): Path to the file to write
- `content` (string, required): Content to write
- `mode` (string, optional): Write mode - 'w' for write (overwrite), 'a' for append (default: w)
- `encoding` (string, optional): File encoding (default: utf-8)

**Returns:** Success message with file path

**Example:**
```json
{
  "name": "write_file",
  "parameters": {
    "path": "C:\\Users\\Documents\\notes.txt",
    "content": "Meeting notes from today...",
    "mode": "w"
  }
}
```

**Error Handling:**
- PermissionError: No write access
- OSError: Disk full or other OS errors

---

### delete_file

Delete a file from the file system. **Use with caution** - this operation cannot be undone.

**Parameters:**
- `path` (string, required): Path to the file to delete

**Returns:** Success message or error

**Example:**
```json
{
  "name": "delete_file",
  "parameters": {
    "path": "C:\\Users\\Downloads\\temp.txt"
  }
}
```

**Error Handling:**
- FileNotFoundError: File doesn't exist
- PermissionError: No delete access
- IsADirectoryError: Path is a directory

---

### move_file

Move or rename a file. Can move files across directories.

**Parameters:**
- `source` (string, required): Source file path
- `destination` (string, required): Destination file path

**Returns:** Success message with new path

**Example:**
```json
{
  "name": "move_file",
  "parameters": {
    "source": "C:\\Users\\Downloads\\file.txt",
    "destination": "C:\\Users\\Documents\\file.txt"
  }
}
```

**Error Handling:**
- FileNotFoundError: Source doesn't exist
- PermissionError: No access to source or destination
- shutil.Error: Cross-device move issues

---

### list_directory

List contents of a directory with optional recursive listing and pattern matching.

**Parameters:**
- `path` (string, required): Directory path to list
- `recursive` (boolean, optional): Whether to list recursively (default: false)
- `pattern` (string, optional): Glob pattern to filter results (default: *)

**Returns:** JSON array of files/directories with metadata (size, modified time, type)

**Example:**
```json
{
  "name": "list_directory",
  "parameters": {
    "path": "C:\\Users\\Documents",
    "recursive": false,
    "pattern": "*.txt"
  }
}
```

**Error Handling:**
- NotADirectoryError: Path is not a directory
- PermissionError: No access to directory

---

### search_files

Recursively search for files matching a pattern.

**Parameters:**
- `root_path` (string, required): Root directory to start search from
- `pattern` (string, required): Glob pattern to match (e.g., '*.py', '**/*.txt')
- `max_results` (integer, optional): Maximum number of results to return (default: 100)

**Returns:** JSON object with results array, count, and truncated flag

**Example:**
```json
{
  "name": "search_files",
  "parameters": {
    "root_path": "C:\\Users\\Projects",
    "pattern": "*.py",
    "max_results": 50
  }
}
```

**Error Handling:**
- PermissionError: Skips inaccessible directories gracefully

---

### get_file_info

Get detailed metadata about a file or directory.

**Parameters:**
- `path` (string, required): Path to the file or directory

**Returns:** JSON object with size, created time, modified time, type, permissions, etc.

**Example:**
```json
{
  "name": "get_file_info",
  "parameters": {
    "path": "C:\\Users\\Documents\\report.pdf"
  }
}
```

**Error Handling:**
- FileNotFoundError: Path doesn't exist
- PermissionError: No access to path

---

## Process Management

### launch_application

Launch an application or executable.

**Parameters:**
- `application` (string, required): Application name or path to executable
- `arguments` (array of strings, optional): Command-line arguments

**Returns:** Process ID and success message

**Example:**
```json
{
  "name": "launch_application",
  "parameters": {
    "application": "notepad",
    "arguments": ["C:\\Users\\Documents\\notes.txt"]
  }
}
```

**Platform-Specific:**
- Windows: Use application names like "notepad", "calc", or full paths
- Linux: Use "gedit", "gnome-calculator", etc.
- macOS: Use "TextEdit", "Calculator", etc.

**Error Handling:**
- FileNotFoundError: Application not found
- PermissionError: No execute permission
- OSError: Other launch errors

---

### list_processes

List all running processes or filter by name.

**Parameters:**
- `filter_name` (string, optional): Filter processes by name (case-insensitive)
- `include_details` (boolean, optional): Include memory usage, CPU percent, username (default: false)

**Returns:** JSON object with count and processes array (limited to 100 results)

**Example:**
```json
{
  "name": "list_processes",
  "parameters": {
    "filter_name": "chrome",
    "include_details": true
  }
}
```

**Error Handling:**
- AccessDenied: Skips processes without access
- NoSuchProcess: Skips processes that terminate during iteration

---

### kill_process

Terminate a process by PID or name. **Use with caution** - forcefully stops processes.

**Parameters:**
- `pid` (integer, optional): Process ID to kill
- `name` (string, optional): Process name to kill (kills all matching)

**Note:** At least one parameter (pid or name) is required.

**Returns:** JSON object with killed process count and details

**Example:**
```json
{
  "name": "kill_process",
  "parameters": {
    "pid": 12345
  }
}
```

**Behavior:**
1. Tries graceful termination first (`terminate()`)
2. Waits 3 seconds
3. Force kills if still running (`kill()`)

**Error Handling:**
- NoSuchProcess: Process doesn't exist
- AccessDenied: No permission to kill process
- TimeoutExpired: Process didn't terminate gracefully

---

### get_process_info

Get detailed information about a specific process.

**Parameters:**
- `pid` (integer, required): Process ID to get information about

**Returns:** JSON object with name, status, CPU percent, memory info, create time, exe path, command line

**Example:**
```json
{
  "name": "get_process_info",
  "parameters": {
    "pid": 12345
  }
}
```

**Error Handling:**
- NoSuchProcess: Process doesn't exist
- AccessDenied: No permission to access process info

---

## Web Browsing

### open_url

Open a URL in the default web browser.

**Parameters:**
- `url` (string, required): URL to open (must include protocol, e.g., https://)
- `new_window` (boolean, optional): Open in new window (default: false)
- `new_tab` (boolean, optional): Open in new tab (default: true)

**Returns:** Success message

**Example:**
```json
{
  "name": "open_url",
  "parameters": {
    "url": "https://github.com",
    "new_tab": true
  }
}
```

**Error Handling:**
- Invalid URL format: Must include protocol and valid domain

---

### search_web

Search the web using a search engine.

**Parameters:**
- `query` (string, required): Search query
- `engine` (string, optional): Search engine to use - 'google', 'bing', or 'duckduckgo' (default: google)

**Returns:** Success message with search URL

**Example:**
```json
{
  "name": "search_web",
  "parameters": {
    "query": "Python automation tutorials",
    "engine": "google"
  }
}
```

**Error Handling:**
- Unknown engine: Must be google, bing, or duckduckgo

---

## Screen Capture

### capture_screenshot

Capture a screenshot of the entire screen or a specific region.

**Parameters:**
- `region` (array of integers, optional): Region to capture as [x, y, width, height]. If not provided, captures full screen.
- `save_path` (string, optional): Path to save the screenshot. If not provided, saves to temporary file.
- `quality` (integer, optional): JPEG quality (1-100). Defaults to config setting.

**Returns:** File path to saved screenshot

**Example:**
```json
{
  "name": "capture_screenshot",
  "parameters": {
    "region": [100, 100, 800, 600],
    "save_path": "C:\\Users\\Screenshots\\screen.png"
  }
}
```

**Error Handling:**
- Invalid region coordinates
- Region exceeds screen bounds
- Permission errors when saving file

**Platform-Specific:**
- Windows: Uses PIL ImageGrab for optimal performance
- Linux: Requires `python3-tk` and `python3-dev` packages
- macOS: May require accessibility permissions in System Preferences

---

### get_screen_size

Get the width and height of the primary screen in pixels.

**Parameters:** None

**Returns:** JSON object with width and height

**Example:**
```json
{
  "name": "get_screen_size",
  "parameters": {}
}
```

**Error Handling:**
- Gracefully handles multi-monitor setups (returns primary screen)

---

### locate_image_on_screen

Find an image on the screen and return its coordinates.

**Prerequisites:**
- **OpenCV Required**: The `confidence` parameter requires `opencv-python` to be installed
- Install with: `pip install opencv-python>=4.8.0`
- Without OpenCV, the tool will work but ignore the `confidence` parameter and use basic image matching

**Parameters:**
- `image_path` (string, required): Path to the image file to locate on screen
- `confidence` (number, optional): Confidence level for image matching (0-1). Default: 0.9. **Requires opencv-python**
- `grayscale` (boolean, optional): Whether to use grayscale matching for better performance. Default: true

**Returns:** JSON object with found status and coordinates (x, y, width, height) if found

**Example:**
```json
{
  "name": "locate_image_on_screen",
  "parameters": {
    "image_path": "C:\\Users\\Images\\button.png",
    "confidence": 0.85,
    "grayscale": true
  }
}
```

**Error Handling:**
- FileNotFoundError: Image file doesn't exist
- ImageNotFoundException: Image not found on screen (returns found: false)
- Warning logged if `confidence` is used without opencv-python installed

**Behavior Without OpenCV:**
- If opencv-python is not installed, the tool falls back to basic image matching
- The `confidence` parameter will be ignored with a warning
- Grayscale matching is disabled in fallback mode
- For best results, install opencv-python: `pip install opencv-python`

**Use Cases:**
- Locate UI elements for automation
- Find specific icons or buttons
- Verify visual state of applications

---

### get_pixel_color

Get the RGB color values of a pixel at the specified screen coordinates.

**Parameters:**
- `x` (integer, required): X coordinate of the pixel
- `y` (integer, required): Y coordinate of the pixel

**Returns:** JSON object with r, g, b color values

**Example:**
```json
{
  "name": "get_pixel_color",
  "parameters": {
    "x": 500,
    "y": 300
  }
}
```

**Error Handling:**
- Coordinates out of screen bounds

**Use Cases:**
- Detect UI state by color
- Verify visual elements
- Color sampling for automation logic

---

## Keyboard & Mouse Control

> **⚠️ WARNING**: These tools directly control your keyboard and mouse. Use with caution and always review commands before execution.

### Safety Features

All keyboard and mouse tools include:
- **Failsafe**: Move mouse to screen corner to abort operations (configurable via `FAILSAFE_ENABLED`)
- **Automatic delays**: Configurable delays between actions to prevent system overload (via `AUTOMATION_DELAY_MS`)
- **Coordinate validation**: All coordinates are validated against screen bounds
- **Comprehensive logging**: All automation actions are logged with full parameters
- **Confirmation requirement**: Sensitive actions require explicit confirmation when enabled

### Confirmation Mechanism

**Configuration:**
- Set `SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION=true` in `.env` to require confirmation (default: enabled)
- Set to `false` to disable confirmation checks

**Sensitive Tools Requiring Confirmation:**
- `click_mouse` - Mouse clicks can trigger unintended actions
- `type_text` - Text input can modify data
- `press_key` - Key presses can trigger commands
- `hotkey` - Keyboard shortcuts can close apps or trigger system functions
- `drag_mouse` - Dragging can move/modify UI elements

**Non-Sensitive Tools (No Confirmation Required):**
- `move_mouse` - Only moves cursor, no actions triggered
- `scroll_mouse` - Low-impact scrolling

**How to Confirm:**
When confirmation is required, add `"confirmed": true` to the parameters:
```json
{
  "name": "hotkey",
  "parameters": {
    "keys": ["ctrl", "c"],
    "confirmed": true
  }
}
```

**Error Response Without Confirmation:**
```json
{
  "success": false,
  "error": "This action requires confirmation. Set 'confirmed': true or disable SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION in config."
}
```

### move_mouse

Move the mouse cursor to absolute or relative coordinates.

**Parameters:**
- `x` (integer, required): X coordinate (absolute or relative)
- `y` (integer, required): Y coordinate (absolute or relative)
- `duration` (number, optional): Duration of movement in seconds. Default: 0.5
- `relative` (boolean, optional): Whether coordinates are relative to current position. Default: false

**Returns:** Success message

**Example:**
```json
{
  "name": "move_mouse",
  "parameters": {
    "x": 500,
    "y": 300,
    "duration": 1.0,
    "relative": false
  }
}
```

**Error Handling:**
- Coordinates out of screen bounds (for absolute movement)
- FailSafeException: User moved mouse to corner to abort

---

### click_mouse

Perform mouse clicks at current position or specified coordinates.

**Parameters:**
- `x` (integer, optional): X coordinate. If not provided, clicks at current position.
- `y` (integer, optional): Y coordinate. If not provided, clicks at current position.
- `button` (string, optional): Mouse button - 'left', 'right', or 'middle'. Default: 'left'
- `clicks` (integer, optional): Number of clicks (1=single, 2=double, 3=triple). Default: 1
- `interval` (number, optional): Interval between clicks in seconds. Default: 0.1

**Returns:** Success message

**Example:**
```json
{
  "name": "click_mouse",
  "parameters": {
    "x": 500,
    "y": 300,
    "button": "left",
    "clicks": 2
  }
}
```

**Error Handling:**
- Coordinates out of screen bounds
- FailSafeException: User aborted operation

---

### scroll_mouse

Scroll the mouse wheel up (positive) or down (negative).

**Parameters:**
- `amount` (integer, required): Scroll amount (positive=up, negative=down). Units are platform-dependent.
- `x` (integer, optional): X coordinate to scroll at
- `y` (integer, optional): Y coordinate to scroll at

**Returns:** Success message

**Example:**
```json
{
  "name": "scroll_mouse",
  "parameters": {
    "amount": 5,
    "x": 500,
    "y": 300
  }
}
```

**Platform-Specific:**
- Windows: Amount represents "clicks" of scroll wheel
- Linux: May vary by desktop environment
- macOS: Smooth scrolling supported

---

### type_text

Type text using keyboard input.

**Parameters:**
- `text` (string, required): Text to type
- `interval` (number, optional): Interval between keystrokes in seconds. Default: 0.05

**Returns:** Success message with character count

**Example:**
```json
{
  "name": "type_text",
  "parameters": {
    "text": "Hello, World!",
    "interval": 0.1
  }
}
```

**Error Handling:**
- FailSafeException: User aborted operation
- Special characters may not work on all platforms

**Note:** For special keys (Enter, Tab, etc.), use `press_key` instead.

---

### press_key

Press keyboard keys including special keys.

**Parameters:**
- `key` (string or array of strings, required): Key or array of keys to press in sequence. Supports special keys like 'enter', 'tab', 'esc', 'space', 'backspace', 'delete', 'up', 'down', 'left', 'right', 'home', 'end', 'pageup', 'pagedown', 'f1'-'f12', etc.
- `presses` (integer, optional): Number of times to press the key(s). Default: 1
- `interval` (number, optional): Interval between presses in seconds. Default: 0.1

**Returns:** Success message

**Example:**
```json
{
  "name": "press_key",
  "parameters": {
    "key": ["enter", "tab", "enter"],
    "presses": 1
  }
}
```

**Supported Special Keys:**
- Navigation: 'up', 'down', 'left', 'right', 'home', 'end', 'pageup', 'pagedown'
- Editing: 'backspace', 'delete', 'insert'
- Control: 'enter', 'tab', 'esc', 'space'
- Function: 'f1' through 'f12'
- Modifiers: 'ctrl', 'alt', 'shift', 'win' (Windows), 'command' (macOS)

---

### hotkey

Execute keyboard shortcuts by pressing multiple keys simultaneously.

**Parameters:**
- `keys` (array of strings, required): Array of keys to press simultaneously. Example: ['ctrl', 'c'] for copy, ['ctrl', 'alt', 'delete'] for task manager.

**Returns:** Success message

**Example:**
```json
{
  "name": "hotkey",
  "parameters": {
    "keys": ["ctrl", "shift", "esc"]
  }
}
```

**Common Hotkeys:**
- Copy: ['ctrl', 'c'] (Windows/Linux) or ['command', 'c'] (macOS)
- Paste: ['ctrl', 'v'] (Windows/Linux) or ['command', 'v'] (macOS)
- Task Manager: ['ctrl', 'shift', 'esc'] (Windows)
- Screenshot: ['win', 'shift', 's'] (Windows)

**⚠️ WARNING**: Some hotkeys can close applications or trigger system functions. Use with caution.

---

### drag_mouse

Drag the mouse from current position or specified start to end coordinates.

**Parameters:**
- `x` (integer, required): Target X coordinate (absolute or relative)
- `y` (integer, required): Target Y coordinate (absolute or relative)
- `duration` (number, optional): Duration of drag in seconds. Default: 1.0
- `button` (string, optional): Mouse button to hold during drag - 'left', 'right', or 'middle'. Default: 'left'
- `relative` (boolean, optional): Whether coordinates are relative to current position. Default: false

**Returns:** Success message

**Example:**
```json
{
  "name": "drag_mouse",
  "parameters": {
    "x": 800,
    "y": 600,
    "duration": 1.5,
    "button": "left"
  }
}
```

**Use Cases:**
- Drag and drop files
- Select text or UI elements
- Move windows or objects

---

## Security Considerations

### Path Validation
- All file paths are resolved to absolute paths using `Path.resolve()`
- Prevents path traversal attacks
- Validates that paths exist before operations

### Permission Handling
- All tools gracefully handle `PermissionError`
- Clear error messages indicate access issues
- No silent failures

### Process Safety
- `kill_process` tries graceful termination before force kill
- Process operations require explicit PIDs or names
- No wildcard process termination

### Automation Safety
- **Screen capture**: Validates coordinates and region bounds before capture
- **Keyboard/mouse control**: Includes failsafe mechanism (move mouse to corner to abort)
- **Automatic delays**: Configurable delays prevent system overload
- **Logging**: All automation actions are logged with full parameters
- **Dangerous operations**: Hotkeys that could close applications are logged with warnings

### Best Practices
1. **Review before execution**: Always review file deletion and process termination commands
2. **Use specific paths**: Avoid wildcards in critical operations
3. **Test in safe environment**: Try commands on test files first
4. **Check permissions**: Ensure you have necessary permissions before operations
5. **Backup important data**: Always maintain backups before bulk operations
6. **Enable failsafe**: Keep failsafe enabled for keyboard/mouse automation
7. **Monitor automation**: Watch automated actions to catch unexpected behavior

---

## Platform-Specific Notes

### Windows
- File paths use backslashes: `C:\Users\Documents\file.txt`
- Common applications: `notepad`, `calc`, `mspaint`
- Process names: `chrome.exe`, `notepad.exe`
- PyAutoGUI works natively for automation
- PIL ImageGrab provides optimal screenshot performance

### Linux
- File paths use forward slashes: `/home/user/documents/file.txt`
- Common applications: `gedit`, `gnome-calculator`, `firefox`
- Process names: `chrome`, `gedit`, `python3`
- **Dependencies required**: `sudo apt-get install python3-tk python3-dev` (Debian/Ubuntu)
- May need `scrot` or `gnome-screenshot` for screenshots on some systems

### macOS
- File paths use forward slashes: `/Users/user/Documents/file.txt`
- Common applications: `TextEdit`, `Calculator`, `Safari`
- Process names: `Google Chrome`, `TextEdit`, `python3`
- **Accessibility permissions**: May be required in System Preferences → Security & Privacy → Privacy → Accessibility
- PyAutoGUI works natively for automation

---

## Example Usage

### File Organization
```
User: "Create a folder structure for my project"
Agent: Uses write_file to create README.md, .gitignore, etc.

User: "Find all large files in Downloads"
Agent: Uses search_files with pattern "*" and filters by size

User: "Move all PDFs from Downloads to Documents"
Agent: Uses search_files to find PDFs, then move_file for each
```

### Process Management
```
User: "Launch notepad with my todo list"
Agent: Uses launch_application with path to todo.txt

User: "Show me all Chrome processes"
Agent: Uses list_processes with filter_name="chrome"

User: "Kill the frozen calculator app"
Agent: Uses list_processes to find PID, then kill_process
```

### Web Automation
```
User: "Open GitHub in my browser"
Agent: Uses open_url with https://github.com

User: "Search for Python tutorials"
Agent: Uses search_web with query="Python tutorials"
```

### Screen Automation
```
User: "Take a screenshot of my screen"
Agent: Uses capture_screenshot to save full screen

User: "Find the submit button on screen"
Agent: Uses locate_image_on_screen with button image

User: "What's the screen resolution?"
Agent: Uses get_screen_size to get dimensions
```

### Keyboard & Mouse Automation
```
User: "Click at position 500, 300"
Agent: Uses click_mouse with coordinates

User: "Type 'Hello World' in the active window"
Agent: Uses type_text with the message

User: "Press Ctrl+C to copy"
Agent: Uses hotkey with ['ctrl', 'c']

User: "Drag from current position to 800, 600"
Agent: Uses drag_mouse to perform drag operation
```

---

## Troubleshooting

### Common Issues

**"Permission denied" errors:**
- Run application with appropriate permissions
- Check file/directory ownership
- Verify user has necessary access rights

**"File not found" errors:**
- Verify path is correct
- Check for typos in file names
- Ensure file hasn't been moved or deleted

**"Process not found" errors:**
- Process may have already terminated
- Verify PID is correct
- Check process name spelling

**Path issues on Windows:**
- Use raw strings or double backslashes: `C:\\Users\\...`
- Or use forward slashes: `C:/Users/...`
- Avoid mixing slash types

**PyAutoGUI failsafe triggered:**
- Mouse moved to screen corner (intentional safety feature)
- Disable failsafe in config if needed (not recommended)
- Keep mouse away from corners during automation

**Screenshot not working on Linux:**
- Install required packages: `sudo apt-get install python3-tk python3-dev`
- May need additional tools: `sudo apt-get install scrot`

**Accessibility permission errors on macOS:**
- Go to System Preferences → Security & Privacy → Privacy → Accessibility
- Add Terminal or your Python executable to allowed apps

---

## Future Enhancements

Planned features for future releases:
- Clipboard operations (copy/paste)
- Network operations (download files, API calls)
- Database operations
- Archive operations (zip/unzip)
- System settings management
- OCR (Optical Character Recognition) for screen text extraction
- Advanced image recognition and AI-powered UI element detection

---

*For more information, see the main [README.md](../README.md) or [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md)*
