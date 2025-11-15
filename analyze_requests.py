import os
import pandas as pd
from datetime import datetime
import json

CSV_PATH = "patient_requests_log.csv"

# -----------------------------------------
# 1. Load CSV
# -----------------------------------------
def load_data():
    """Loads data from the CSV file."""
    if not os.path.exists(CSV_PATH):
        print("No CSV log detected. Cannot analyze.")
        return None
    # Add a simple check for file size to prevent errors on empty files
    if os.path.getsize(CSV_PATH) == 0:
        print("CSV log file is empty. Cannot analyze.")
        return None
    try:
        # Assuming the CSV is well-formed for basic loading
        return pd.read_csv(CSV_PATH)
    except pd.errors.EmptyDataError:
        print("CSV log file is empty or malformed. Cannot analyze.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the CSV: {e}")
        return None

# -----------------------------------------
# 2. Add useful engineered features
# -----------------------------------------
def enrich(df):
    """Adds 'timestamp', 'hour', and 'day' features to the DataFrame."""
    # Ensure 'timestamp' column exists before operating on it
    if 'timestamp' not in df.columns:
        print("Error: 'timestamp' column not found in DataFrame.")
        return df

    # Original code had unit='s', which assumes the timestamp is in seconds (Unix time)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
    # Drop rows where timestamp conversion failed (if 'errors' was not 'coerce', it would raise an error)
    df.dropna(subset=['timestamp'], inplace=True)

    df['hour'] = df['timestamp'].dt.hour
    df['day'] = df['timestamp'].dt.date.astype(str)  # string for JSON
    return df

# -----------------------------------------
# 3. Compute statistics for frontend charts
# -----------------------------------------
def compute_stats(df):
    """Computes basic statistics for requests."""
    total = len(df)
    
    # Ensure 'request' column exists for value_counts and groupby
    if 'request' not in df.columns:
        requests_by_type = {}
        print("Warning: 'request' column not found for type statistics.")
    else:
        # Use value_counts() to get counts for each unique request type
        requests_by_type = df['request'].value_counts().to_dict()
    
    # Ensure 'hour' and 'day' columns exist for grouping
    if 'hour' not in df.columns or 'day' not in df.columns:
        requests_by_hour = {}
        requests_by_day = {}
        print("Warning: 'hour' or 'day' columns not found for time statistics.")
    else:
        # Group by 'hour' and count requests
        requests_by_hour = df.groupby('hour')['request'].count().to_dict()
        # Group by 'day' and count requests
        requests_by_day = df.groupby('day')['request'].count().to_dict()

    stats = {
        "total_requests": total,
        "requests_by_type": requests_by_type,
        "requests_by_hour": requests_by_hour,
        "requests_by_day": requests_by_day
    }
    return stats

# -----------------------------------------
# 4. Human/Rule-Based Insights (AI Replacement)
# -----------------------------------------
def human_insights(stats):
    """
    Placeholder function for AI insights. 
    Can be expanded with rule-based analysis if required, 
    but for now, it simply states the AI insights are unavailable.
    """
    # You could add simple rule-based analysis here, e.g.:
    # - Identify the most common request type.
    # - Find the peak hour for requests.
    # ---
    
    # Example of a simple placeholder response:
    return (
        "--- Insights (AI Functionality Disabled) ---\n"
        "AI-Powered Operational Insights are unavailable because the "
        "Gemini API functionality has been intentionally removed from this script.\n\n"
        "To perform a manual analysis, focus on the following:\n"
        "* **Peak Times:** Analyze 'requests_by_hour' to identify staff allocation needs.\n"
        "* **Top Requests:** Analyze 'requests_by_type' to identify the most common patient needs (e.g., Pain Medication, Restroom) which may suggest operational gaps (like scheduled pain management rounds or improved pre-emptive assistance).\n"
        "* **Daily Trends:** Analyze 'requests_by_day' to spot unusual spikes or drops."
    )

# -----------------------------------------
# 5. Function to return JSON-ready data
# -----------------------------------------
def get_analysis_json():
    """Main function to load, process, and return analysis data."""
    df = load_data()
    if df is None or df.empty:
        # Added a check for an empty DataFrame
        return {"error": "No valid data found or CSV log is empty"}

    df = enrich(df)
    stats = compute_stats(df)
    # Replaced ai_insights with human_insights (or rule-based equivalent)
    insights = human_insights(stats)

    return {
        stats
    }

# -----------------------------------------
# 6. Standalone test
# -----------------------------------------
if __name__ == "__main__":
    result = get_analysis_json()
    # Use json.dumps to print the final structure
    print(json.dumps(result, indent=2))
