from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import pickle
import json
import os

# --- 1. Initialization ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# --- 2. Load All Assets on Startup ---
print("Loading application assets...")
try:
    with open(os.path.join(BASE_DIR, 'fruit_model_v4.pkl'), 'rb') as f:
        model = pickle.load(f)
    print("Model 'fruit_model_v4.pkl' loaded successfully.")

    with open(os.path.join(BASE_DIR, 'model_v4_columns.json'), 'r') as f:
        model_columns = json.load(f)
    print("Model columns 'model_v4_columns.json' loaded successfully.")

    with open(os.path.join(BASE_DIR, 'fruits_database_finalv2.json'), 'r') as f:
        fruit_database = json.load(f)
    print("Fruit database 'fruits_database_finalv2.json' loaded successfully.")

    with open(os.path.join(BASE_DIR, 'locations_master.json'), 'r') as f:
        locations_master = json.load(f)
    print("Locations data 'locations_master.json' loaded successfully.")

except FileNotFoundError as e:
    print(f"FATAL ERROR: A required asset file was not found: {e}")
    model = None
    model_columns = []
    fruit_database = {}
    locations_master = {}

print("--- Application Ready ---")


# --- 3. API Endpoints ---
@app.route('/health', methods=['GET'])
def health():
    """Simple health check for uptime monitoring."""
    is_ready = bool(model) and isinstance(locations_master, dict) and len(locations_master) > 0
    return jsonify({
        "status": "ok" if is_ready else "degraded",
        "model_loaded": bool(model),
        "locations_count": len(locations_master) if isinstance(locations_master, dict) else 0
    })


@app.route('/', methods=['GET'])
def index():
    """Serve the frontend."""
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/get_locations', methods=['GET'])
def get_locations():
    if locations_master:
        return jsonify(locations_master)
    else:
        return jsonify({"error": "Locations data not available"}), 500


# In main.py, replace the entire @app.route('/recommend') function with this one.

@app.route('/recommend', methods=['POST'])
def recommend():
    """
    The core recommendation logic endpoint.
    Implements "Smart Sorting" for health goals.
    """
    if not model:
        return jsonify({"error": "Model is not loaded. Cannot provide recommendations."}), 500

    data = request.get_json(force=True, silent=True) or {}
    month, state, district = data.get('month'), data.get('state'), data.get('district')
    health_focus = data.get('health_focus', [])

    if not all([month, state, district]):
        return jsonify({"error": "Missing required fields: month, state, district"}), 400

    # Validate provided values if locations_master is available
    if isinstance(locations_master, dict) and locations_master:
        if state not in locations_master:
            return jsonify({"error": f"Unknown state: {state}"}), 400
        if district not in locations_master.get(state, []):
            return jsonify({"error": f"Unknown district '{district}' for state '{state}'"}), 400

    # Step 1 & 2: Candidate Generation and AI Scoring (Unchanged)
    candidates = []
    for fruit_name, details in fruit_database.items():
        try:
            for variety_name, variety_info in details.get('varieties', {}).items():
                peak_states = variety_info.get('peak_states', {})
                # Support both dict (state -> districts) and list of states
                state_match = False
                if isinstance(peak_states, dict):
                    state_match = state in peak_states
                elif isinstance(peak_states, list):
                    state_match = state in peak_states
                if state_match:
                    candidates.append({
                        "fruit_name": fruit_name,
                        "variety": variety_name,
                        "state": state,
                        "district": district,
                        "month": month
                    })
        except Exception:
            continue
    if not candidates:
        return jsonify([])

    candidates_df = pd.DataFrame(candidates)
    test_encoded = pd.get_dummies(candidates_df)
    test_aligned = test_encoded.reindex(columns=model_columns, fill_value=0)
    predictions = model.predict(test_aligned)
    candidates_df['model_score'] = predictions

    # Step 3: Enrichment (Unchanged)
    results = []
    for idx, candidate in candidates_df.iterrows():
        if candidate['model_score'] <= 0.1:
            continue

        fruit_name, variety_name = candidate['fruit_name'], candidate['variety']
        fruit_details = fruit_database.get(fruit_name, {})
        variety_details = fruit_details.get('varieties', {}).get(variety_name, {})

        final_score = candidate['model_score']
        health_tags = fruit_details.get('health_tags', [])
        if health_focus and any(tag in health_tags for tag in health_focus):
            final_score *= 1.15

        season_status = ""
        model_score = candidate['model_score']
        if model_score > 0.6: season_status = "is at its absolute peak"
        elif model_score > 0.3: season_status = "is currently in season"
        else: season_status = "season is just beginning"

        specialty_districts = []
        peak_states = variety_details.get('peak_states', {})
        if isinstance(peak_states, dict):
            specialty_districts = peak_states.get(state, [])
        origin_text = ""
        if specialty_districts:
            origin_text = f"from the {specialty_districts[0]} region" if len(specialty_districts) == 1 else f"from the {', '.join(specialty_districts[:-1])} and {specialty_districts[-1]} regions"
        
        reason = f"Fresh {origin_text} of {state}, the {variety_name} variety's {season_status}!"
        
        # Prefer variety-specific image, fallback to fruit-level image
        image_url = variety_details.get('image_url') or fruit_details.get('image_url', '')
        results.append({
            'fruit_name': fruit_name,
            'variety': variety_name,
            'score': round(final_score, 4),
            'image_url': image_url,
            'reason': reason,
            'benefits': fruit_details.get('benefits', 'No description available.'),
            'health_tags': health_tags
        })

    # --- Step 4: NEW Smart Sorting and De-duplication Logic ---
    sorted_results = []
    if health_focus:
        # Sort by: any_match, match_count, score
        def sort_key(r):
            tags = set(r.get('health_tags', []))
            hf = set(health_focus)
            match_count = len(tags.intersection(hf))
            return (match_count > 0, match_count, r['score'])
        results.sort(key=sort_key, reverse=True)
        sorted_results = results
    else:
        # If no health focus, sort by score as usual
        sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)

    final_recommendations = []
    displayed_fruits = set()
    for rec in sorted_results:
        if rec['fruit_name'] not in displayed_fruits:
            final_recommendations.append(rec)
            displayed_fruits.add(rec['fruit_name'])
    
    return jsonify(final_recommendations)


# --- 4. Run the Application ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)