import sys
from typing import Optional
from .auth import get_credentials
from .sheet_client import SheetClient
from .tui.app import SheetEditor

def print_help():
    """Print help information."""
    print("Google Sheets TUI Editor")
    print("\nUsage:")
    print("  gsheet <sheet_id>         # Open sheet by ID")
    print("  gsheet @<shortcut>        # Open sheet by shortcut name")
    print("  gsheet --add <name> <id>  # Add a new shortcut")
    print("  gsheet --list             # List all shortcuts")
    print("  gsheet --help             # Show this help message")
    print("\nExamples:")
    print("  gsheet 1t54f4aRu9kQAW7r8FYV9pzJSqAs8-isc")
    print("  gsheet @timesheet")
    print("  gsheet --add timesheet 1t54f4aRu9kQAW7r8FYV9pzJSqAs8-isc")

def handle_shortcuts(client: SheetClient, args: list[str]) -> Optional[str]:
    """
    Handle shortcut-related commands.
    
    Returns:
        Optional[str]: Sheet ID to open, or None if no sheet should be opened
    """
    if args[1] == '--add':
        if len(args) != 4:
            print("Error: --add requires a name and sheet ID")
            print("Usage: gsheet --add <name> <sheet_id>")
            return None
            
        name, sheet_id = args[2], args[3]
        client.add_shortcut(name, sheet_id)
        print(f"Added shortcut '@{name}' -> '{sheet_id}'")
        return None
        
    elif args[1] == '--list':
        shortcuts = client.list_shortcuts()
        if not shortcuts:
            print("No shortcuts defined")
        else:
            print("Available shortcuts:")
            for name, sheet_id in shortcuts.items():
                print(f"  @{name}: {sheet_id}")
        return None
        
    elif args[1] == '--help':
        print_help()
        return None
        
    elif args[1].startswith('@'):
        shortcut_name = args[1][1:]
        sheet_id = client.get_shortcut(shortcut_name)
        if not sheet_id:
            print(f"Unknown shortcut: {shortcut_name}")
            print("\nAvailable shortcuts:")
            for name, id in client.list_shortcuts().items():
                print(f"  @{name}: {id}")
            return None
        return sheet_id
        
    return args[1]

def main():
    """Main entry point for the application."""
    # Get credentials
    creds = get_credentials()
    if not creds:
        print("Failed to get credentials")
        sys.exit(1)
        
    # Initialize sheet client
    client = SheetClient(creds)
    
    # Show help if no arguments
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
        
    # Handle commands and shortcuts
    sheet_id = handle_shortcuts(client, sys.argv)
    if not sheet_id:
        sys.exit(0)
    
    # Open sheet
    success, error_message = client.open_sheet(sheet_id)
    if not success:
        print(f"Failed to open sheet: {error_message}")
        sys.exit(1)
        
    # Run the TUI app
    app = SheetEditor(client)
    app.run()

if __name__ == "__main__":
    main() 