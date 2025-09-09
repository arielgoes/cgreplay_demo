#!/usr/bin/env python3
"""
Flask Web Application for QoE Statistics Dashboard
Provides API endpoints to serve analysis data from Google Sheets
"""

import os
import sys
import json
from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Import analysis functions from the existing script
try:
    from analyze_all_qoe_data_from_google_sheet import (
        authenticate_google_sheets, get_data_from_google_sheets, 
        analyze_data, is_synthetic
    )
    print("Successfully imported analysis functions")
except ImportError as e:
    print(f"Warning: Could not import analysis functions: {e}")
    print("Using simplified analysis functions without visualization dependencies")
    
    def authenticate_google_sheets():
        raise Exception("Google Sheets authentication not available")
    
    def get_data_from_google_sheets():
        raise Exception("Google Sheets data fetching not available")
    
    def is_synthetic(filename):
        return "interpolated" in filename.lower()
    
    def analyze_data(df):
        """Simplified analysis function that works without matplotlib/seaborn."""
        import pandas as pd
        import numpy as np
        
        print(f"DataFrame shape: {df.shape}")
        print(f"DataFrame columns: {df.columns.tolist()}")
        
        # Handle empty dataset case
        if df.empty or len(df) == 0:
            print("Dataset is empty, returning zero values")
            return {
                'df': pd.DataFrame(),
                'overall_accuracy': 0.0,
                'accuracy_by_type': {},
                'accuracy_by_user': pd.Series(dtype=float),
                'confusion_matrix': pd.DataFrame()
            }
        
        # Create a working copy
        df_work = df.copy()
        
        # Remove rows with missing critical data
        df_work = df_work.dropna(subset=['User ID', 'Video A Filename', 'Video B Filename', 'Which Video Real'])
        
        # Check again after cleaning
        if df_work.empty or len(df_work) == 0:
            print("Dataset is empty after cleaning, returning zero values")
            return {
                'df': pd.DataFrame(),
                'overall_accuracy': 0.0,
                'accuracy_by_type': {},
                'accuracy_by_user': pd.Series(dtype=float),
                'confusion_matrix': pd.DataFrame()
            }
        
        # Map the 'Which Video Real' column to standardized format
        def map_user_guess(value):
            if pd.isna(value):
                return 'Unknown'
            value_str = str(value).lower().strip()
            if value_str in ['a', 'video a', 'left']:
                return 'Video A is Real'
            elif value_str in ['b', 'video b', 'right']:
                return 'Video B is Real'
            elif value_str in ['both', 'both are real', 'neither']:
                return 'Both are Real'
            elif value_str in ['none', 'none are real', 'both synthetic']:
                return 'None are Real'
            else:
                return 'Unknown'
        
        df_work['User Guess'] = df_work['Which Video Real'].apply(map_user_guess)
        
        # Determine if videos are synthetic
        df_work['Video A Is Synthetic'] = df_work['Video A Filename'].apply(is_synthetic)
        df_work['Video B Is Synthetic'] = df_work['Video B Filename'].apply(is_synthetic)
        
        # Determine the actual reality
        def determine_reality(row):
            a_synthetic = row['Video A Is Synthetic']
            b_synthetic = row['Video B Is Synthetic']
            
            if not a_synthetic and not b_synthetic:
                return 'Both are Real'
            elif a_synthetic and b_synthetic:
                return 'None are Real'
            elif not a_synthetic and b_synthetic:
                return 'Video A is Real'
            else:
                return 'Video B is Real'
        
        df_work['Reality'] = df_work.apply(determine_reality, axis=1)
        
        # Determine if the user's guess was correct
        df_work['Correct Guess'] = df_work.apply(
            lambda row: row['User Guess'] == row['Reality'], axis=1
        )
        
        # Calculate overall accuracy
        overall_accuracy = df_work['Correct Guess'].mean() if len(df_work) > 0 else 0.0
        
        # Calculate accuracy by video type
        accuracy_by_type = {}
        for reality in df_work['Reality'].unique():
            subset = df_work[df_work['Reality'] == reality]
            if len(subset) > 0:
                accuracy = subset['Correct Guess'].mean()
                accuracy_by_type[reality] = accuracy
        
        # Calculate accuracy by user
        accuracy_by_user = df_work.groupby('User ID')['Correct Guess'].mean()
        
        # Create simple confusion matrix
        reality_categories = ['Video A is Real', 'Video B is Real', 'Both are Real', 'None are Real']
        
        try:
            if len(df_work) > 0:
                confusion_matrix = pd.crosstab(
                    df_work['Reality'], 
                    df_work['User Guess'],
                    normalize='index'
                )
                
                # Ensure all categories are present
                for category in reality_categories:
                    if category not in confusion_matrix.index:
                        confusion_matrix.loc[category] = 0
                    if category not in confusion_matrix.columns:
                        confusion_matrix[category] = 0
                
                confusion_matrix = confusion_matrix.reindex(reality_categories, axis=0, fill_value=0)
                confusion_matrix = confusion_matrix.reindex(reality_categories, axis=1, fill_value=0)
            else:
                confusion_matrix = pd.DataFrame(
                    0, 
                    index=reality_categories, 
                    columns=reality_categories
                )
        except Exception as e:
            print(f"Warning: Could not create confusion matrix: {e}")
            confusion_matrix = pd.DataFrame(
                0, 
                index=reality_categories, 
                columns=reality_categories
            )
        
        return {
            'df': df_work,
            'overall_accuracy': overall_accuracy,
            'accuracy_by_type': accuracy_by_type,
            'accuracy_by_user': accuracy_by_user,
            'confusion_matrix': confusion_matrix
        }

except Exception as e:
    print(f"Error importing analysis functions: {e}")
    # Define fallback functions
    def authenticate_google_sheets():
        raise Exception("Google Sheets authentication not available")
    
    def get_data_from_google_sheets():
        raise Exception("Google Sheets data fetching not available")
    
    def analyze_data(df):
        raise Exception("Data analysis functions not available")
    
    def is_synthetic(filename):
        return "interpolated" in filename.lower()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Cache for data to avoid frequent API calls
data_cache = {
    'data': None,
    'timestamp': None
}
CACHE_DURATION = 300  # 5 minutes in seconds

def download_fresh_data():
    """Download fresh data from Google Sheets using the download script."""
    import subprocess
    
    try:
        print("Downloading fresh data from Google Sheets...")
        result = subprocess.run([sys.executable, 'download_all_qoe_data_from_google_sheet.py'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("Fresh data downloaded successfully")
            return True
        else:
            print(f"Download script failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("Download script timed out")
        return False
    except Exception as e:
        print(f"Error running download script: {e}")
        return False

def get_cached_data(force_refresh=False):
    """Get cached analysis data or fetch fresh data if cache is expired."""
    import time
    
    current_time = time.time()
    
    # Check if we need to force refresh or cache is expired
    if (not force_refresh and 
        data_cache['data'] is not None and 
        data_cache['timestamp'] is not None and
        current_time - data_cache['timestamp'] < CACHE_DURATION):
        return data_cache['data']
    
    # Try to download fresh data first if force_refresh is True
    if force_refresh:
        download_fresh_data()
    
    # Try CSV file first, then Google Sheets, then mock data
    try:
        # Check for CSV file first
        csv_files = ['all_qoe_data_from_google_sheet.csv']
        for csv_file in csv_files:
            if os.path.exists(csv_file):
                print(f"Loading data from CSV file: {csv_file}")
                df = pd.read_csv(csv_file)
                results = analyze_data(df)
                
                # Update cache
                data_cache['data'] = results
                data_cache['timestamp'] = current_time
                
                return results
        
        # Try Google Sheets if no CSV found
        if os.path.exists('credentials.json'):
            print("Fetching fresh data from Google Sheets...")
            df = get_data_from_google_sheets()
            results = analyze_data(df)
            
            # Update cache
            data_cache['data'] = results
            data_cache['timestamp'] = current_time
            
            return results
        else:
            print("No CSV file or credentials.json found. Using mock data for demonstration.")
            return generate_mock_data()
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        # Return cached data if available, even if expired
        if data_cache['data'] is not None:
            print("Returning expired cached data due to error")
            return data_cache['data']
        else:
            # Return mock data for testing if no real data available
            print("Falling back to mock data for demonstration")
            return generate_mock_data()

def generate_mock_data():
    """Generate mock data for testing when real data is not available."""
    import pandas as pd
    import numpy as np
    
    # Create mock dataframe
    mock_data = {
        'User ID': ['user1', 'user2', 'user3', 'user4', 'user5'] * 4,
        'Video A Filename': ['original_video.mp4', 'interpolated_video.mp4'] * 10,
        'Video B Filename': ['interpolated_video.mp4', 'original_video.mp4'] * 10,
        'Which Video Real': ['a', 'b', 'both', 'none'] * 5,
        'Video A Score': np.random.randint(1, 6, 20),
        'Video B Score': np.random.randint(1, 6, 20),
    }
    
    df = pd.DataFrame(mock_data)
    
    # Apply analysis logic
    df['Video A Is Synthetic'] = df['Video A Filename'].apply(is_synthetic)
    df['Video B Is Synthetic'] = df['Video B Filename'].apply(is_synthetic)
    
    # Determine reality and user guess
    def determine_reality(row):
        a_synthetic = row['Video A Is Synthetic']
        b_synthetic = row['Video B Is Synthetic']
        
        if not a_synthetic and not b_synthetic:
            return 'Both are Real'
        elif a_synthetic and b_synthetic:
            return 'None are Real'
        elif not a_synthetic and b_synthetic:
            return 'Video A is Real'
        else:
            return 'Video B is Real'
    
    df['Reality'] = df.apply(determine_reality, axis=1)
    
    df['User Guess'] = df['Which Video Real'].apply(
        lambda x: {
            'a': 'Video A is Real',
            'b': 'Video B is Real', 
            'both': 'Both are Real',
            'none': 'None are Real'
        }.get(str(x).lower(), 'Unknown')
    )
    
    df['Correct Guess'] = df.apply(
        lambda row: row['User Guess'] == row['Reality'], axis=1
    )
    
    # Calculate results
    overall_accuracy = df['Correct Guess'].mean()
    accuracy_by_type = df.groupby('Reality')['Correct Guess'].mean().to_dict()
    accuracy_by_user = df.groupby('User ID')['Correct Guess'].mean()
    
    confusion_matrix = pd.crosstab(
        df['Reality'], 
        df['User Guess'],
        normalize='index'
    )
    
    return {
        'df': df,
        'overall_accuracy': overall_accuracy,
        'accuracy_by_type': accuracy_by_type,
        'accuracy_by_user': accuracy_by_user,
        'confusion_matrix': confusion_matrix
    }

@app.route('/')
def index():
    """Serve the main evaluation page."""
    return send_from_directory('.', 'index.html')

@app.route('/stats')
def stats_page():
    """Serve the statistics dashboard page."""
    return send_from_directory('.', 'stats.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_csv():
    """Handle CSV file upload."""
    from flask import request, redirect, url_for, flash
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename.endswith('.csv'):
            # Save the uploaded file
            filename = 'all_qoe_data_from_google_sheet.csv'
            file.save(filename)
            
            # Clear cache to force reload
            data_cache['data'] = None
            data_cache['timestamp'] = None
            
            return jsonify({'message': 'File uploaded successfully', 'redirect': '/stats'})
        else:
            return jsonify({'error': 'Please upload a CSV file'}), 400
    
    # GET request - show upload form
    upload_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload QoE Data</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
            .upload-box { border: 2px dashed #ccc; padding: 40px; text-align: center; border-radius: 10px; }
            .upload-box:hover { border-color: #999; }
            input[type="file"] { margin: 20px 0; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .back-link { display: block; margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>Upload QoE Data CSV</h1>
        <div class="upload-box">
            <h3>📁 Upload your CSV file</h3>
            <p>Download your data from Google Sheets and upload it here</p>
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" name="file" accept=".csv" required>
                <br>
                <button type="submit">Upload CSV</button>
            </form>
        </div>
        <a href="/stats" class="back-link">← Back to Statistics</a>
        
        <script>
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                
                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        alert('File uploaded successfully!');
                        window.location.href = '/stats';
                    } else {
                        alert('Error: ' + result.error);
                    }
                } catch (error) {
                    alert('Upload failed: ' + error.message);
                }
            });
        </script>
    </body>
    </html>
    '''
    return upload_html

@app.route('/api/stats/overview')
def stats_overview():
    """Get overall statistics summary."""
    try:
        # Check if this is a refresh request
        from flask import request
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        results = get_cached_data(force_refresh=force_refresh)
        
        # Handle empty dataset case
        if results is None or results.get('df') is None or len(results.get('df', pd.DataFrame())) == 0:
            overview = {
                'total_evaluations': 0,
                'unique_users': 0,
                'overall_accuracy': 0.0,
                'video_type_distribution': {},
                'accuracy_by_type': {}
            }
            return jsonify(overview)
        
        # Calculate additional metrics
        df = results['df']
        total_evaluations = len(df)
        unique_users = df['User ID'].nunique() if 'User ID' in df.columns else 0
        
        # Get video type distribution
        video_type_counts = {}
        if 'Reality' in df.columns:
            for _, row in df.iterrows():
                reality = row['Reality']
                video_type_counts[reality] = video_type_counts.get(reality, 0) + 1
        
        # Handle accuracy_by_type safely
        accuracy_by_type = results.get('accuracy_by_type', {})
        safe_accuracy_by_type = {}
        for k, v in accuracy_by_type.items():
            safe_accuracy_by_type[k] = float(v) if not pd.isna(v) else 0.0
        
        # Handle overall accuracy safely
        overall_accuracy = results.get('overall_accuracy', 0.0)
        safe_overall_accuracy = float(overall_accuracy) if not pd.isna(overall_accuracy) else 0.0
        
        overview = {
            'total_evaluations': int(total_evaluations),
            'unique_users': int(unique_users),
            'overall_accuracy': safe_overall_accuracy,
            'video_type_distribution': video_type_counts,
            'accuracy_by_type': safe_accuracy_by_type
        }
        
        return jsonify(overview)
    
    except Exception as e:
        print(f"Error in stats_overview endpoint: {e}")
        import traceback
        traceback.print_exc()
        # Return empty data structure instead of error
        overview = {
            'total_evaluations': 0,
            'unique_users': 0,
            'overall_accuracy': 0.0,
            'video_type_distribution': {},
            'accuracy_by_type': {}
        }
        return jsonify(overview)

@app.route('/api/stats/user_accuracy')
@app.route('/api/stats/user/accuracy')
def user_accuracy():
    """Get user accuracy distribution data."""
    try:
        from flask import request
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        results = get_cached_data(force_refresh=force_refresh)
        
        # Handle case where accuracy_by_user might be empty or have issues
        accuracy_by_user = results['accuracy_by_user']
        
        # Convert pandas Series to list safely
        if hasattr(accuracy_by_user, 'tolist'):
            user_accuracies = accuracy_by_user.tolist()
        else:
            user_accuracies = list(accuracy_by_user) if accuracy_by_user else []
        
        # Handle potential NaN values
        user_accuracies = [float(x) if not pd.isna(x) else 0.0 for x in user_accuracies]
        
        # Calculate mean and std safely
        if len(user_accuracies) > 0:
            mean_accuracy = sum(user_accuracies) / len(user_accuracies)
            if len(user_accuracies) > 1:
                variance = sum((x - mean_accuracy) ** 2 for x in user_accuracies) / len(user_accuracies)
                std_accuracy = variance ** 0.5
            else:
                std_accuracy = 0.0
        else:
            mean_accuracy = 0.0
            std_accuracy = 0.0
        
        accuracy_data = {
            'user_accuracies': user_accuracies,
            'overall_accuracy': float(results['overall_accuracy']) if not pd.isna(results['overall_accuracy']) else 0.0,
            'mean_accuracy': float(mean_accuracy),
            'std_accuracy': float(std_accuracy)
        }
        
        return jsonify(accuracy_data)
    
    except Exception as e:
        print(f"Error in user_accuracy endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats/user/<user_id>')
def user_specific_stats(user_id):
    """Get statistics for a specific user."""
    try:
        from flask import request
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        results = get_cached_data(force_refresh=force_refresh)
        df = results['df']
        
        # Filter data for specific user
        user_data = df[df['User ID'] == user_id]
        
        if len(user_data) == 0:
            return jsonify({'error': f'No data found for user ID: {user_id}'}), 404
        
        # Calculate user-specific metrics
        user_accuracy = user_data['Correct Guess'].mean()
        total_evaluations = len(user_data)
        
        # User's accuracy by video type
        user_accuracy_by_type = {}
        for reality in user_data['Reality'].unique():
            subset = user_data[user_data['Reality'] == reality]
            if len(subset) > 0:
                accuracy = subset['Correct Guess'].mean()
                user_accuracy_by_type[reality] = accuracy
        
        # User's evaluation details
        evaluations = []
        for _, row in user_data.iterrows():
            evaluations.append({
                'scene': row.get('Scene', 'Unknown'),
                'video_a': row['Video A Filename'],
                'video_b': row['Video B Filename'],
                'video_a_score': row.get('Video A Score', 'N/A'),
                'video_b_score': row.get('Video B Score', 'N/A'),
                'reality': row['Reality'],
                'user_guess': row['User Guess'],
                'correct': bool(row['Correct Guess'])
            })
        
        # Compare to overall statistics
        overall_accuracy = results['overall_accuracy']
        performance_vs_average = user_accuracy - overall_accuracy
        
        user_stats = {
            'user_id': user_id,
            'total_evaluations': total_evaluations,
            'user_accuracy': float(user_accuracy),
            'overall_accuracy': float(overall_accuracy),
            'performance_vs_average': float(performance_vs_average),
            'accuracy_by_type': {k: float(v) for k, v in user_accuracy_by_type.items()},
            'evaluations': evaluations,
            'rank': None  # Will calculate below
        }
        
        # Calculate user rank
        all_user_accuracies = results['accuracy_by_user'].sort_values(ascending=False)
        user_rank = list(all_user_accuracies.index).index(user_id) + 1 if user_id in all_user_accuracies.index else None
        user_stats['rank'] = user_rank
        user_stats['total_users'] = len(all_user_accuracies)
        
        return jsonify(user_stats)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats/detailed')
def detailed_stats():
    """Get detailed statistics for advanced analysis."""
    try:
        results = get_cached_data()
        df = results['df']
        
        # Calculate additional detailed metrics
        detailed = {
            'total_responses': len(df),
            'unique_participants': df['User ID'].nunique(),
            'responses_per_user': df.groupby('User ID').size().tolist(),
            'accuracy_by_user': results['accuracy_by_user'].to_dict(),
            'video_pairs_evaluated': df.groupby(['Video A Filename', 'Video B Filename']).size().to_dict(),
            'common_mistakes': [],
            'best_performing_scenarios': [],
            'worst_performing_scenarios': []
        }
        
        # Find common mistakes (incorrect guesses)
        incorrect_responses = df[~df['Correct Guess']]
        if len(incorrect_responses) > 0:
            mistake_patterns = incorrect_responses.groupby(['Reality', 'User Guess']).size().sort_values(ascending=False)
            detailed['common_mistakes'] = [
                {
                    'actual': reality,
                    'guessed': guess,
                    'count': int(count)
                }
                for (reality, guess), count in mistake_patterns.head(5).items()
            ]
        
        # Best and worst performing scenarios
        accuracy_by_type = results['accuracy_by_type']
        sorted_accuracies = sorted(accuracy_by_type.items(), key=lambda x: x[1], reverse=True)
        
        detailed['best_performing_scenarios'] = [
            {'scenario': scenario, 'accuracy': float(accuracy)}
            for scenario, accuracy in sorted_accuracies[:3]
        ]
        
        detailed['worst_performing_scenarios'] = [
            {'scenario': scenario, 'accuracy': float(accuracy)}
            for scenario, accuracy in sorted_accuracies[-3:]
        ]
        
        return jsonify(detailed)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'QoE Statistics API'})

# Serve static files
@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('.', filename)

if __name__ == '__main__':
    print("Starting QoE Statistics Server...")
    print("Make sure you have:")
    print("1. credentials.json file for Google Sheets access")
    print("2. Flask and required dependencies installed")
    
    # Get port from environment variable (Render sets this automatically)
    port = int(os.environ.get('PORT', 5000))
    # Only enable debug mode in local development, not in production
    debug_mode = os.environ.get('FLASK_ENV') == 'development' and port == 5000
    
    print(f"\nServer will be available on port: {port}")
    print("Statistics dashboard: /stats")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
