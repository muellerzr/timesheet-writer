from textual.app import App
from textual.widgets import DataTable, Header, Footer, Input, Select
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Input
from textual.widgets._data_table import CellDoesNotExist
from textual.message import Message
from ..sheet_client import SheetClient
from datetime import datetime

class EditScreen(Screen):
    """Screen for editing cell value."""
    
    def __init__(self, row: int, current_value: str, is_new_row: bool = False):
        """
        Initialize edit screen.
        
        Args:
            row: Row number (1-based)
            current_value: Current value of the merged cells
            is_new_row: Whether this is a new row being added
        """
        super().__init__()
        self.row = row
        self.current_value = current_value
        self.is_new_row = is_new_row
        
    def compose(self):
        action = "Add New Row" if self.is_new_row else f"Edit Row {self.row}"
        yield Header(action)
        yield Input(
            value=self.current_value,
            placeholder="Enter hours (format: 1, 2, 3, 4)",
            id="hours_input"
        )
        yield Footer()
        
    def on_input_submitted(self, event: Input.Submitted):
        """Handle input submission."""
        if event.input.id == "hours_input":
            # Split the input into 4 values and update cells B through E
            values = {}
            hours = [h.strip() for h in event.value.split(',')]
            
            # Pad with empty strings if fewer than 4 values provided
            hours.extend([''] * (4 - len(hours)))
            
            # Map the first 4 values to columns B through E
            for i, hour in enumerate(hours[:4]):
                values[i + 2] = hour  # +2 because we start at column B (index 2)
            
            self.app.update_row(self.row, values, is_new_row=self.is_new_row)
            self.app.pop_screen()

class ShortcutScreen(Screen):
    """Screen for managing sheet shortcuts."""
    
    def compose(self):
        yield Header("Sheet Shortcuts")
        yield DataTable()
        yield Input(placeholder="Shortcut name")
        yield Input(placeholder="Sheet ID")
        yield Footer()
        
    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("Name", "Sheet ID")
        
        # Load existing shortcuts
        shortcuts = self.app.sheet_client.list_shortcuts()
        for name, sheet_id in shortcuts.items():
            table.add_row(name, sheet_id)

class SheetEditor(App):
    """A terminal user interface for editing Google Sheets."""
    
    BINDINGS = [
        Binding("e", "edit_row", "Edit Cell"),
        Binding("t", "insert_time", "Insert Time"),
        Binding("w", "switch_worksheet", "Switch Sheet"),
        Binding("n", "new_shortcut", "New Shortcut"),
        Binding("q", "quit", "Save & Quit"),
        Binding("Q", "quit_without_save", "Quit (No Save)"),
    ]
    
    CSS = """
    Screen {
        align: center middle;
    }
    
    DataTable {
        height: 1fr;
        border: solid green;
    }
    
    Select {
        width: 100%;
    }
    """
    
    def __init__(self, sheet_client: SheetClient):
        super().__init__()
        self.sheet_client = sheet_client
        
    def compose(self):
        """Create child widgets for the app."""
        yield Header()
        
        worksheet_options = [(name, name) for name in self.sheet_client.get_worksheets()]
        
        yield Container(
            Select(
                worksheet_options,
                prompt="Select Worksheet",
                id="worksheet_select"
            ),
            DataTable(id="sheet_table")
        )
        yield Footer()
        
    def on_mount(self):
        """Load initial data."""
        # Focus on the worksheet selector without loading data
        select = self.query_one("#worksheet_select", Select)
        select.focus()
        
    def on_select_changed(self, event: Select.Changed):
        """Handle worksheet selection."""
        if event.select.id == "worksheet_select" and event.value:
            success, error = self.sheet_client.switch_worksheet(event.value)
            if success:
                self._refresh_data()
                # Focus on the data table after switching worksheet
                table = self.query_one("#sheet_table", DataTable)
                table.focus()
            else:
                print(f"Failed to switch worksheet: {error}")
        
    def _refresh_data(self):
        """Refresh the displayed data."""
        if not self.sheet_client.current_worksheet:
            return
            
        table = self.query_one("#sheet_table", DataTable)
        data = self.sheet_client.get_data()
        
        # Clear existing data
        table.clear()
        
        # Add columns using the sheet's headers
        if data and len(data) > 0:
            # Always use first row as headers
            headers = data[0]
            
            # Add the columns
            table.add_columns(*headers)
            
            # Add the data rows (skip header row)
            for row in data[1:]:
                table.add_row(*row)
                
    async def action_switch_worksheet(self):
        """Handle worksheet switching."""
        select = self.query_one("#worksheet_select", Select)
        select.focus()
                
    async def action_edit_row(self):
        """Handle row editing."""
        table = self.query_one("#sheet_table", DataTable)
        cursor_row = table.cursor_row
        
        if cursor_row is not None:
            # Get current data length (excluding header)
            data_length = len(table.rows) - 1  # -1 for header row
            
            # Print debug info
            print(f"Cursor row: {cursor_row}, Data length: {data_length}")
            
            # Determine if this is a new row
            is_new_row = cursor_row >= data_length
            
            if is_new_row:
                print("Creating new row")
                current_values = [""] * 4  # Empty values for B through E
                # Use the actual cursor position for the new row
                actual_row = cursor_row + 1
            else:
                print("Editing existing row")
                # Get existing values from columns B through E
                current_values = []
                for col in range(1, 5):  # B through E
                    try:
                        value = table.get_cell(cursor_row, col) or ""
                        current_values.append(value)
                    except (CellDoesNotExist, KeyError):
                        current_values.append("")
                actual_row = cursor_row + 1
            
            current_value = ", ".join(current_values)
            print(f"Opening edit screen for row {actual_row} (is_new_row: {is_new_row})")
            await self.push_screen(EditScreen(actual_row, current_value, is_new_row))
            
    def update_row(self, row: int, values: dict[int, str], is_new_row: bool = False):
        """Update cells in a row."""
        success = True
        error_msg = ""
        
        try:
            table = self.query_one("#sheet_table", DataTable)
            print(f"Updating row {row} (is_new_row: {is_new_row})")
            
            if is_new_row:
                # Directly append the row to both the sheet and the table
                success, error_msg = self.sheet_client.append_row(values)
            else:
                # Update existing row cells
                for col, value in values.items():
                    cell_success, cell_error = self.sheet_client.update_cell(row, col, value)
                    if not cell_success:
                        success = False
                        error_msg = cell_error
                        break
            
            if success:
                # Immediately push changes
                push_success, push_msg = self.sheet_client.push_changes()
                if not push_success:
                    print(f"Failed to push changes: {push_msg}")
                
                # Get fresh data
                data = self.sheet_client.get_data()
                
                # Clear and rebuild table
                table.clear()
                if data and len(data) > 0:
                    headers = data[0]
                    table.add_columns(*headers)
                    for row_data in data[1:]:
                        table.add_row(*row_data)
                
                # Move cursor to the correct row
                target_row = len(table.rows) - 1 if is_new_row else row - 1
                if target_row < len(table.rows):
                    table.move_cursor(row=target_row, column=1)
                    table.scroll_to_row(target_row)
            else:
                print(f"Failed to update row: {error_msg}")
                
        except Exception as e:
            print(f"Error updating row: {str(e)}")
            
    async def action_new_shortcut(self):
        """Handle creating new shortcuts."""
        await self.push_screen(ShortcutScreen())
        
    async def action_list_shortcuts(self):
        """Show list of shortcuts."""
        await self.push_screen(ShortcutScreen())
        
    async def action_quit_without_save(self) -> None:
        """Quit without saving changes."""
        # Exit immediately without pushing changes
        self.exit()
        
    async def action_quit(self) -> None:
        """Handle quit action with changes push."""
        # Push any pending changes
        success, message = self.sheet_client.push_changes()
        if not success:
            print(f"Warning: {message}")
        
        # Quit the application
        self.exit()
        
    async def action_insert_time(self):
        """Insert current time at cursor position."""
        table = self.query_one("#sheet_table", DataTable)
        cursor_row = table.cursor_row
        cursor_col = table.cursor_column
        
        if cursor_row is not None and cursor_col is not None:
            # Format as time only (e.g., "14:30" for Google Sheets time format)
            current_time = datetime.now().strftime("%H:%M")
            
            # Get current data length (excluding header)
            data_length = len(table.rows) - 1  # -1 for header row
            
            # Determine if this is a new row
            is_new_row = cursor_row >= data_length
            
            # Create TIME formula without quotes, always use 00 for seconds
            hour, minute = current_time.split(':')
            time_formula = f"=TIME({int(hour)}, {int(minute)}, 00)"
            
            if is_new_row:
                # For new rows, we need to append
                values = {cursor_col + 1: time_formula}
                success, error_msg = self.sheet_client.append_row(values)
            else:
                # For existing rows, update the cell with TIME formula
                success, error_msg = self.sheet_client.update_cell(
                    cursor_row + 1, 
                    cursor_col + 1, 
                    time_formula
                )
            
            if success:
                # Immediately push changes
                push_success, push_msg = self.sheet_client.push_changes()
                if not push_success:
                    print(f"Failed to push time update: {push_msg}")
                
                # Refresh display
                self._refresh_data()
                
                # Move cursor back to the edited position and ensure it's visible
                target_row = len(table.rows) - 1 if is_new_row else cursor_row
                if target_row < len(table.rows):
                    table.move_cursor(row=target_row, column=cursor_col, scroll=True)
            else:
                print(f"Failed to insert time: {error_msg}")
            
    async def action_save_changes(self):
        """Save all pending changes."""
        success, message = self.sheet_client.push_changes()
        if not success:
            print(f"Failed to save changes: {message}")
        else:
            print("Changes saved successfully")
            # Refresh the display
            self._refresh_data() 