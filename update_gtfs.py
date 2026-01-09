import requests
import zipfile
import io
import os
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

# Correct, direct URL to the ZIP file
URL = "https://kochimetro.org/opendata/KMRLOpenData.zip"
DB_URL = "sqlite:///metro.db"
LOCAL_GTFS_DIR = "gtfs_data"
ENGINE = create_engine(DB_URL)

def process_gtfs_files(gtfs_path):
    """Loads all .txt files from a given path into the database."""
    print(f"📁 Processing GTFS files from '{gtfs_path}'...")
    files_to_process = [f for f in os.listdir(gtfs_path) if f.endswith('.txt')]
    
    if not files_to_process:
        print("❌ No .txt files found in the directory.")
        return

    for file in files_to_process:
        table_name = file.replace(".txt", "")
        df = pd.read_csv(os.path.join(gtfs_path, file))
        df.to_sql(table_name, ENGINE, if_exists="replace", index=False)
        print(f"✅ Table '{table_name}' updated with {len(df)} rows.")

def update_gtfs():
    # --- Step 1: Try downloading the live feed from the correct URL ---
    try:
        print(f"🔄 Attempting to download live GTFS feed from {URL}...")
        response = requests.get(URL, timeout=60)
        response.raise_for_status() # Raise an exception for bad status codes
        
        print("📥 Live feed downloaded successfully. Extracting...")
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(LOCAL_GTFS_DIR)
        
        process_gtfs_files(LOCAL_GTFS_DIR)
        return # Success, so we exit the function

    except (requests.exceptions.RequestException, zipfile.BadZipFile) as e:
        print(f"⚠️ Could not download or process the live feed: {e}")

    # --- Step 2: Fallback to local 'gtfs_data' directory ---
    print(f"\n↪️ Falling back to local directory '{LOCAL_GTFS_DIR}'...")
    if os.path.exists(LOCAL_GTFS_DIR) and 'stops.txt' in os.listdir(LOCAL_GTFS_DIR):
        print("👍 Found existing local GTFS data.")
        process_gtfs_files(LOCAL_GTFS_DIR)
        return # Success, so we exit
    else:
        print(f"❌ Local directory '{LOCAL_GTFS_DIR}' not found or is empty.")

    # --- Step 3: Instruct user if all else fails ---
    print("\n" + "="*50)
    print("‼️ DATABASE SETUP FAILED: Could not find GTFS data.")
    print("Please perform the following manual step:")
    print("1. Go to this Google Drive link:")
    print("   https://drive.google.com/drive/folders/1YRCnrvSbdyQxb1v8Y-o7NUL3y0xfEosu")
    print("2. Download the files and place them in a folder named 'gtfs_data'")
    print("   in the same directory as this script.")
    print("3. Run this script again.")
    print("="*50)


if __name__ == "__main__":
    update_gtfs()
    if os.path.exists('metro.db'):
        with open("last_update.txt", "w") as f:
            f.write(datetime.now().isoformat())
            print("\n✨ Database update process finished.")