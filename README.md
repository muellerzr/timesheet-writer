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
   (1t54f4aRu9kQAW7r8FYV9pzJSqAs8-isc)

2. Run the application:
```bash
gsheet-tui 1t54f4aRu9kQAW7r8FYV9pzJSqAs8-isc
```

## Controls

- Arrow keys: Navigate cells
- E: Edit current cell
- S: Save changes
- Q: Quit application