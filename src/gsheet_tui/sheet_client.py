from typing import List, Optional, Tuple, Dict
import gspread
from google.oauth2.credentials import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound
from googleapiclient.discovery import build
import json
import os
import re
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class PendingChange:
    row: int
    col: int
    value: str

class SheetClient:
    def __init__(self, credentials: Credentials):
        """
        Initialize the Google Sheets client.
        
        Args:
            credentials (Credentials): Google OAuth credentials
        """
        self.client = gspread.authorize(credentials)
        self.drive_service = build('drive', 'v3', credentials=credentials)
        self.current_sheet = None
        self.current_worksheet = None
        self.shortcuts_file = 'sheet_shortcuts.json'
        self.shortcuts = self._load_shortcuts()
        self.cached_data: List[List[str]] = []
        self.pending_changes: Dict[str, List[PendingChange]] = defaultdict(list)
        
    def _load_shortcuts(self) -> Dict[str, str]:
        """Load sheet shortcuts from file."""
        if os.path.exists(self.shortcuts_file):
            with open(self.shortcuts_file, 'r') as f:
                return json.load(f)
        return {}
        
    def _save_shortcuts(self):
        """Save sheet shortcuts to file."""
        with open(self.shortcuts_file, 'w') as f:
            json.dump(self.shortcuts, f, indent=2)
            
    def add_shortcut(self, name: str, sheet_id: str) -> None:
        """Add or update a sheet shortcut."""
        self.shortcuts[name] = sheet_id
        self._save_shortcuts()
        
    def get_shortcut(self, name: str) -> Optional[str]:
        """Get sheet ID from shortcut name."""
        return self.shortcuts.get(name)
        
    def list_shortcuts(self) -> Dict[str, str]:
        """Get all shortcuts."""
        return self.shortcuts
        
    def get_worksheets(self) -> List[str]:
        """Get names of all worksheets in current sheet."""
        if not self.current_sheet:
            return []
        return [ws.title for ws in self.current_sheet.worksheets()]
        
    def switch_worksheet(self, worksheet_name: str) -> tuple[bool, str]:
        """Switch to a different worksheet."""
        try:
            if not self.current_sheet:
                return False, "No sheet is currently open"
                
            # Get the new worksheet
            self.current_worksheet = self.current_sheet.worksheet(worksheet_name)
            
            # Clear cached data to force refresh
            self.cached_data = []
            
            # Clear any pending changes for the previous worksheet
            if self.current_worksheet:
                self.cached_data = self.current_worksheet.get_all_values()
                return True, ""
            return False, "Failed to access worksheet"
                
        except Exception as e:
            return False, f"Failed to switch worksheet: {str(e)}"
        
    def _is_excel_file(self, sheet_id: str) -> bool:
        """Check if the ID matches Excel file pattern."""
        return bool(re.search(r'-isc$', sheet_id))

    def _convert_to_sheets_format(self, file_id: str) -> Optional[str]:
        """
        Convert Excel file to Google Sheets format using Drive API.
        
        Args:
            file_id (str): The Excel file ID
            
        Returns:
            Optional[str]: New Google Sheet ID if successful, None otherwise
        """
        try:
            # Get the original file metadata
            file = self.drive_service.files().get(
                fileId=file_id.replace('-isc', ''),
                fields='name'
            ).execute()

            # Create a copy in Google Sheets format
            metadata = {
                'name': f"{file['name']} (Converted)",
                'mimeType': 'application/vnd.google-apps.spreadsheet'
            }
            
            # Copy the file with conversion
            result = self.drive_service.files().copy(
                fileId=file_id.replace('-isc', ''),
                body=metadata
            ).execute()
            
            return result['id']
            
        except Exception as e:
            print(f"Conversion error: {str(e)}")
            return None
        
    def open_sheet(self, sheet_id_or_name: str) -> tuple[bool, str]:
        """
        Open a Google Sheet by ID or shortcut name.
        
        Args:
            sheet_id_or_name (str): The Google Sheet/Excel ID or shortcut name
            
        Returns:
            tuple[bool, str]: (Success status, Error message if any)
        """
        try:
            # Check if it's a shortcut name
            sheet_id = self.shortcuts.get(sheet_id_or_name, sheet_id_or_name)
            
            if self._is_excel_file(sheet_id):
                # Convert Excel to Google Sheets format
                new_id = self._convert_to_sheets_format(sheet_id)
                if not new_id:
                    return False, "Failed to convert Excel file to Google Sheets format"
                self.current_sheet = self.client.open_by_key(new_id)
            else:
                self.current_sheet = self.client.open_by_key(sheet_id)
            
            # Default to first worksheet
            self.current_worksheet = self.current_sheet.sheet1
            return True, ""
            
        except SpreadsheetNotFound:
            return False, f"Sheet '{sheet_id_or_name}' not found"
        except APIError as e:
            if "PERMISSION_DENIED" in str(e):
                return False, f"Permission denied for '{sheet_id_or_name}'"
            return False, f"API Error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
            
    def get_data(self) -> List[List[str]]:
        """Get all values from the current worksheet."""
        if not self.current_worksheet:
            return []
            
        # Get fresh data if cache is empty
        if not self.cached_data:
            try:
                self.cached_data = self.current_worksheet.get_all_values()
            except Exception as e:
                print(f"Error fetching data: {str(e)}")
                return []
                    
        # Apply any pending changes to a copy of the cached data
        data = [row[:] for row in self.cached_data]  # Make a copy
        
        if self.current_sheet and self.current_worksheet:
            worksheet_key = f"{self.current_sheet.id}:{self.current_worksheet.title}"
            changes = self.pending_changes.get(worksheet_key, [])
            
            # Apply pending changes
            for change in changes:
                # Ensure we have enough rows
                while len(data) <= change.row:
                    data.append([''] * (len(data[0]) if data else 5))  # Default to 5 columns if empty
                    
                # Ensure we have enough columns in this row
                while len(data[change.row]) <= change.col:
                    data[change.row].append('')
                    
                # Apply the change
                data[change.row][change.col] = change.value
                
        return data
        
    def update_cell(self, row: int, col: int, value: str) -> tuple[bool, str]:
        """Queue a cell update."""
        try:
            if not self.current_worksheet or not self.current_sheet:
                return False, "No worksheet is currently open"
                
            # Get worksheet key
            worksheet_key = f"{self.current_sheet.id}:{self.current_worksheet.title}"
            
            # Convert to 0-based indices for internal storage
            row_idx = row - 1
            col_idx = col - 1
            
            # Add the change
            change = PendingChange(row_idx, col_idx, value)
            self.pending_changes[worksheet_key].append(change)
            
            # Ensure cached data exists
            if not self.cached_data:
                self.cached_data = self.current_worksheet.get_all_values()
            
            # Ensure cached data has enough rows
            while len(self.cached_data) <= row_idx:
                if self.cached_data:
                    new_row = [''] * len(self.cached_data[0])
                else:
                    new_row = [''] * 5
                self.cached_data.append(new_row)
            
            # Ensure the row has enough columns
            while len(self.cached_data[row_idx]) <= col_idx:
                self.cached_data[row_idx].append('')
            
            # Update the cached data
            self.cached_data[row_idx][col_idx] = value
            
            return True, ""
            
        except Exception as e:
            return False, f"Error: {str(e)}"
            
    def append_row(self, values: dict[int, str]) -> tuple[bool, str]:
        """Append a new row to the worksheet using Google Sheets API."""
        try:
            if not self.current_worksheet or not self.current_sheet:
                return False, "No worksheet is currently open"
            
            # Create a row array with empty values
            row_data = [''] * len(self.cached_data[0])
            
            # Fill in the provided values
            for col, value in values.items():
                if col - 1 < len(row_data):
                    row_data[col - 1] = value
            
            # Use the actual append_row method from gspread
            self.current_worksheet.append_row(row_data, value_input_option='USER_ENTERED')
            
            # Update our cached data
            if not self.cached_data:
                self.cached_data = self.current_worksheet.get_all_values()
            else:
                self.cached_data.append(row_data)
            
            return True, ""
            
        except Exception as e:
            return False, f"Error appending row: {str(e)}"

    def push_changes(self) -> tuple[bool, str]:
        """Push all pending changes to Google Sheets."""
        if not self.pending_changes:
            return True, "No changes to push"
            
        try:
            for worksheet_key, changes in self.pending_changes.items():
                sheet_id, worksheet_title = worksheet_key.split(':')
                
                # Switch to the correct worksheet if needed
                if (not self.current_sheet or 
                    str(self.current_sheet.id) != sheet_id or 
                    self.current_worksheet.title != worksheet_title):
                    self.current_sheet = self.client.open_by_key(sheet_id)
                    self.current_worksheet = self.current_sheet.worksheet(worksheet_title)

                # Create batch update data
                batch_data = []
                for change in changes:
                    # Convert to A1 notation
                    col_letter = chr(65 + change.col)  # A=65, B=66, etc.
                    row_num = change.row + 1  # Convert to 1-based
                    cell_range = f"{col_letter}{row_num}"
                    
                    batch_data.append({
                        'range': cell_range,
                        'values': [[change.value]]  # Double array as per API spec
                    })

                # Execute batch update with proper value input option
                if batch_data:
                    self.current_worksheet.batch_update(
                        batch_data,
                        value_input_option='USER_ENTERED'  # Important for formulas
                    )

            # Clear pending changes and refresh cache
            self.pending_changes.clear()
            self.cached_data = self.current_worksheet.get_all_values()
            
            return True, "Changes pushed successfully"
            
        except Exception as e:
            print(f"Debug - Push error: {str(e)}")  # Debug print
            return False, f"Failed to push changes: {str(e)}"

    def insert_row(self, row: int) -> None:
        """Insert a new empty row at the specified position in cached data."""
        row_idx = row - 1  # Convert to 0-based index
        
        # Ensure we have cached data
        if not self.cached_data:
            self.cached_data = self.current_worksheet.get_all_values()
        
        # Create empty row with same width as existing data
        empty_row = [''] * (len(self.cached_data[0]) if self.cached_data else 5)
        
        # Insert the row at the specified position
        if row_idx >= len(self.cached_data):
            self.cached_data.append(empty_row)
        else:
            self.cached_data.insert(row_idx, empty_row)

    def append_row(self, values: dict[int, str]) -> tuple[bool, str]:
        """Append a new row to the worksheet."""
        try:
            if not self.current_worksheet or not self.current_sheet:
                return False, "No worksheet is currently open"
            
            # Ensure we have cached data
            if not self.cached_data:
                self.cached_data = self.current_worksheet.get_all_values()
            
            # Create an empty row with the same width as existing data
            row_data = [''] * len(self.cached_data[0])
            
            # Fill in the provided values
            for col, value in values.items():
                if col - 1 < len(row_data):  # Convert to 0-based index
                    row_data[col - 1] = value
            
            # Get the next row index (1-based)
            next_row = len(self.cached_data)
            
            # Store as pending change
            worksheet_key = f"{self.current_sheet.id}:{self.current_worksheet.title}"
            for col, value in values.items():
                change = PendingChange(
                    row=next_row,  # This will be the index of the new row
                    col=col-1,
                    value=value
                )
                self.pending_changes[worksheet_key].append(change)
            
            # Update cached data
            self.cached_data.append(row_data)
            
            return True, ""
            
        except Exception as e:
            return False, f"Error appending row: {str(e)}" 