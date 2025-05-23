import zipfile
import os

zip_path = r"C:\Users\jdmc8\CryptoBotBackup.zip"
extract_dir = r"C:\Temp\CryptoBotBackup"

# Create extraction directory if it doesn't exist
os.makedirs(extract_dir, exist_ok=True)

# Extract the zip file
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_dir)

print(f"Extracted files to {extract_dir}")