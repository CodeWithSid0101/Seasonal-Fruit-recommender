import os
import json
import requests
import time

# --- CONFIGURATION ---
# PASTE YOUR PEXELS API KEY HERE
PEXELS_API_KEY = "ql6BSSpqTnycDcfXt4uBD2ynJtITmdPUlWANUxNyZWgXqX5HbFE5ruiu" 
# ---------------------

INPUT_JSON_FILE = 'fruits_database_finalv2.json'
OUTPUT_JSON_FILE = 'fruits_database_finalv3.json' # We'll create a new file
IMAGE_DIR = os.path.join('static', 'images')

def search_and_download_image(fruit_name, pexels_headers):
    """Searches for a fruit on Pexels and downloads the first result."""
    print(f"Searching for '{fruit_name}'...")
    
    # Pexels API search endpoint
    search_url = f"https://api.pexels.com/v1/search?query={fruit_name} fruit&per_page=1"
    
    try:
        response = requests.get(search_url, headers=pexels_headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        
        if data['photos']:
            # Get the URL for a medium-sized image
            image_url = data['photos'][0]['src']['medium']
            
            # Download the image
            image_data = requests.get(image_url).content
            
            # Create a clean filename
            filename = f"{fruit_name.lower().replace(' ', '_')}.jpg"
            filepath = os.path.join(IMAGE_DIR, filename)
            
            # Save the image to the static/images folder
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # Return the local path for the JSON file
            local_path = f"/static/images/{filename}"
            print(f"  -> Success! Image saved to {filepath}")
            return local_path
        else:
            print(f"  -> No results found for '{fruit_name}' on Pexels.")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"  -> API Error for '{fruit_name}': {e}")
        return None

def main():
    if PEXELS_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: Please paste your Pexels API key into the script.")
        return

    # Create the static/images directory if it doesn't exist
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    # Load the existing fruit database
    with open(INPUT_JSON_FILE, 'r') as f:
        fruit_data = json.load(f)
    
    headers = {"Authorization": PEXELS_API_KEY}
    
    # Loop through each fruit and update its image_url
    for fruit, details in fruit_data.items():
        new_url = search_and_download_image(fruit, headers)
        if new_url:
            # Update the URL in our data to the new local path
            details['image_url'] = new_url
        else:
            # If we fail, keep the old URL as a fallback
            print(f"  -> Could not update image for {fruit}. Keeping old URL.")
        
        # Be respectful to the API and avoid hitting rate limits
        time.sleep(1) 

    # Save the updated data to a new file
    with open(OUTPUT_JSON_FILE, 'w') as f:
        json.dump(fruit_data, f, indent=4)
        
    print(f"\nProcess complete! All data saved to '{OUTPUT_JSON_FILE}'.")
    print("Please update main.py to use this new JSON file.")

if __name__ == '__main__':
    main()