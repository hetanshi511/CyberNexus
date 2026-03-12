import os
import sys

# Add Backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Backend'))

from services.gmail_reader import get_gmail_service

def test_watch():
    print("Testing Gmail Watch registration...")
    try:
        service = get_gmail_service()
        request = {
            "labelIds": ["Interview-Replies"],
            "topicName": "projects/ai-marketplace-c169b/topics/gmail-interview-replies"
        }
        res = service.users().watch(userId="me", body=request).execute()
        print(f"✅ SUCCESS! Gmail watch registered on topic: projects/ai-marketplace-c169b/topics/gmail-interview-replies")
        print(res)
    except Exception as e:
        print(f"❌ ERROR registering watch: {e}")

if __name__ == "__main__":
    test_watch()
