import sys
import os

# Ensure the backend directory is in the path so we can import modules
sys.path.append(os.path.abspath('Backend'))

try:
    from services.gmail_reader import get_gmail_service
except ImportError as e:
    print(f"Failed to import get_gmail_service: {e}")
    sys.exit(1)

def check_gmail_labels():
    print("Fetching Gmail labels...")
    try:
        service = get_gmail_service()
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        if not labels:
            print("No labels found.")
        else:
            print("Labels:")
            for label in labels:
                name = label.get('name', 'Unknown')
                label_id = label.get('id', 'Unknown')
                
                # Highlight if it matches "Interview-Replies"
                if "Interview" in name or "Replies" in name:
                    print(f" ⭐ MATCH: '{name}' -> ID: {label_id}")
                else:
                    print(f"  - '{name}' -> ID: {label_id}")
                    
    except Exception as e:
        print(f"Error fetching labels: {e}")

if __name__ == '__main__':
    check_gmail_labels()
