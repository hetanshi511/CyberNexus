import requests

def download_drive_file(file_id: str, access_token: str) -> tuple[bytes, str, str]:
    """
    Downloads file from Google Drive using file_id.
    Returns: (file_bytes, file_name, mime_type)
    """

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Get file metadata
    meta_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=name,mimeType"
    meta_res = requests.get(meta_url, headers=headers)
    meta_res.raise_for_status()
    meta = meta_res.json()

    file_name = meta["name"]
    mime_type = meta["mimeType"]

    # Download file content
    download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    file_res = requests.get(download_url, headers=headers)
    file_res.raise_for_status()

    return file_res.content, file_name, mime_type
