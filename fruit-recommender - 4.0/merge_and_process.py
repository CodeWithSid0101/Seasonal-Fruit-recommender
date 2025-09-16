import os
import json
import pandas as pd
from collections import defaultdict
import numpy as np
import sys

# --- CONFIGURATION ---
# Get the absolute path of the directory where this script is located
# This makes the script runnable from anywhere.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the paths to your data folders relative to the script's location
STATES_FOLDER = os.path.join(SCRIPT_DIR, 'States')
UT_FOLDER = os.path.join(SCRIPT_DIR, 'Union_Territories')
OUTPUT_DB_FILE = os.path.join(SCRIPT_DIR, 'fruits_database_final.json')
OUTPUT_LOCATIONS_FILE = os.path.join(SCRIPT_DIR, 'locations_master.json')

def process_and_merge_data(paths):
    """
    Reads raw state/UT JSON files, processes them, and aggregates the data
    into a fruit-centric master database and a locations file.
    """
    master_fruit_db = defaultdict(lambda: {
        "health_tags": set(),
        "avg_price_per_kg_inr": [],
        "estimated_user_rating": [],
        "varieties": defaultdict(lambda: {
            "peak_states": set(),
            "peak_months": set()
        })
    })
    
    locations_data = defaultdict(list)
    files_processed_count = 0

    print("--- Starting Data Processing ---")

    for folder_path in paths:
        print(f"\n[INFO] Looking for JSON files in: {folder_path}")
        if not os.path.exists(folder_path):
            print(f"⚠️ [WARNING] Folder not found. Skipping.")
            continue
        
        found_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
        if not found_files:
            print(f"   -> No JSON files found in this folder.")
            continue
        
        print(f"   -> Found {len(found_files)} JSON file(s).")
            
        for filename in found_files:
            filepath = os.path.join(folder_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # --- FIX: Handle the new JSON structure ---
                # Check if the loaded data is a dictionary and has at least one key
                if not isinstance(data, dict) or not data:
                    print(f"   -> ⚠️ Skipping {filename}: File is empty or not a valid JSON object.")
                    continue
                
                # The state name is the top-level key in your new structure
                state_name = list(data.keys())[0]
                state_data = data[state_name] # This is the object containing all the state's info

                print(f"   -> Processing '{state_name}' from {filename}...")

                # Now look for districts inside the state_data object
                districts = state_data.get("major_fruit_districts", {})
                if not districts:
                    print(f"   -> ⚠️ No 'major_fruit_districts' found for {state_name}. Skipping district processing.")
                
                locations_data[state_name] = sorted(list(districts.keys()))

                for district_name, district_info in districts.items():
                    for fruit in district_info.get("fruits", []):
                        fruit_name = fruit.get("fruit_name")
                        if not fruit_name:
                            continue
                        
                        entry = master_fruit_db[fruit_name]
                        entry["health_tags"].update(fruit.get("health_tags", []))
                        entry["avg_price_per_kg_inr"].append(fruit.get("avg_price_per_kg_inr", 0))
                        entry["estimated_user_rating"].append(fruit.get("estimated_user_rating", 0))
                        
                        for variety_name in fruit.get("famous_varieties", []):
                            variety_entry = entry["varieties"][variety_name]
                            variety_entry["peak_states"].add(state_name)
                            variety_entry["peak_months"].update(fruit.get("peak_months", []))
                
                files_processed_count += 1

            except json.JSONDecodeError:
                print(f"   -> ❌ [ERROR] Could not decode JSON from {filename}. Please check for syntax errors. Skipping.")
            except Exception as e:
                print(f"   -> ❌ [ERROR] An unexpected error occurred with {filename}: {e}. Skipping.")


    # --- FINAL SANITY CHECK ---
    if not master_fruit_db:
        print("\n--- ❌ CRITICAL ERROR ---")
        print("No fruit data was collected from your JSON files.")
        print("Please check the following:")
        print("1. Your folder structure is correct: 'fruit-recommender - Copy' should contain 'States' and 'Union_Territories' folders.")
        print("2. Your JSON files are inside these folders.")
        print("3. The JSON files are not empty and follow the correct structure (containing 'state_name', 'major_fruit_districts', etc.).")
        sys.exit(1) # Exit the script

    # --- FINAL PROCESSING & SAVING ---
    print("\n[INFO] Finalizing master database...")
    final_db = {}
    for fruit_name, data in master_fruit_db.items():
        avg_price = int(np.mean(data["avg_price_per_kg_inr"])) if data["avg_price_per_kg_inr"] else 0
        avg_rating = round(np.mean(data["estimated_user_rating"]), 1) if data["estimated_user_rating"] else 0
        
        final_db[fruit_name] = {
            "benefits": f"A popular fruit known for its delicious taste and health benefits related to {', '.join(sorted(list(data['health_tags'])))}.",
            "health_tags": sorted(list(data["health_tags"])),
            "availability_score": 8,
            "avg_price_per_kg": avg_price,
            "user_rating": avg_rating,
            "varieties": {
                var_name: {
                    "peak_states": sorted(list(var_data["peak_states"])),
                    "peak_months": sorted(list(var_data["peak_months"]))
                } for var_name, var_data in data["varieties"].items()
            }
        }
    
    with open(OUTPUT_DB_FILE, 'w') as f:
        json.dump(final_db, f, indent=4)
    print(f"✅ Master database saved to '{OUTPUT_DB_FILE}' with {len(final_db)} unique fruits.")

    with open(OUTPUT_LOCATIONS_FILE, 'w') as f:
        json.dump(dict(sorted(locations_data.items())), f, indent=4)
    print(f"✅ Locations data saved to '{OUTPUT_LOCATIONS_FILE}'.")
    print(f"\n--- 🎉 Successfully processed {files_processed_count} files. ---")


if __name__ == "__main__":
    # Ensure you have pandas and numpy: pip install pandas numpy
    process_and_merge_data([STATES_FOLDER, UT_FOLDER])



