# Google Sheets TUI Editor

A terminal-based user interface for editing Google Sheets. Navigate and edit your spreadsheets directly from the command line.

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the package:
```bash
pip install -e .
```

## Google Sheets API Setup

1. Visit the Google Cloud Console (https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API for your project
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop application"
   - Download the credentials file
5. Save the downloaded file as `credentials.json` in your project directory

## Usage

1. Find your Google Sheet ID from its URL:
   Sheet ID is the long string of characters in:
   https://docs.google.com/spreadsheets/d/SHEET_ID/edit

2. Run the application:
```bash
gsheet @timesheet  # Using a shortcut
# or
gsheet 1t54f4aRu9kQAW7r8FYV9pzJSqAs8-isc  # Using sheet ID directly
```

## Controls

- Arrow keys: Navigate cells
- e: Edit current cell
- t: Insert current time (HH:MM format)
- w: Switch worksheet
- n: Create new shortcut
- q: Quit and save
- Q: Quit without saving (Shift + Q)

## Editing Rows

### Existing Rows
- Navigate to any row and press 'i' to edit
- Enter values separated by commas (e.g., "1, 2, 3, 4")
- Values will be placed in columns B through E

### Adding New Rows
**Important Note**: To add a new row, move the cursor to one row BELOW the last data row. Due to the interface design, you need to be at row N+1 to add a new row after row N.

Example:
```
| Row 1 | Data... |
| Row 2 | Data... |
| Row 3 | Data... |
| [Cursor here] |  <- Move cursor here to add new row
```

## Time Entry
- Navigate to desired cell
- Press 't' to insert current time
- Time will be inserted in proper Google Sheets time format (HH:MM)

## Shortcuts

Add a shortcut:
```bash
gsheet --add timesheet 1t54f4aRu9kQAW7r8FYV9pzJSqAs8-isc
```

List shortcuts:
```bash
gsheet --list
```

Use a shortcut:
```bash
gsheet @timesheet
```

## API Documentation

### Google Sheets Integration

The application uses the following Google Sheets API endpoints:

1. Values API (`/v4/spreadsheets/{spreadsheetId}/values`):
   - Used for reading and writing cell values
   - Handles batch updates for multiple cells
   - Supports formula input via 'USER_ENTERED' input option

2. Batch Update API (`/v4/spreadsheets/{spreadsheetId}:batchUpdate`):
   - Used for structural changes and formatting
   - Handles multiple operations in a single request

### Time Format

Time entries use Google Sheets' TIME function:
```
=TIME(hour, minute, 00)
```
This ensures proper time formatting and calculations in the sheet.

### Row Operations

The application follows these rules for row operations:
1. Edit existing row: Cursor at row N edits row N
2. Add new row: Cursor must be at row N+1 to add after row N
3. Time insertion: Works in both existing and new rows

For technical details, see:
- [Google Sheets API Values Guide](https://developers.google.com/workspace/sheets/api/guides/values)
- [Batch Update Guide](https://developers.google.com/workspace/sheets/api/guides/batchupdate)