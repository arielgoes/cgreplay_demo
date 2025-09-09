#!/usr/bin/env python3
"""
QoE Data Analysis Script

This script extracts data from a Google Sheet containing subjective QoE assessment results,
analyzes when users correctly identified synthetic videos, and generates visualizations.
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Set style for plots
plt.style.use('ggplot')
sns.set(style="whitegrid")

# Constants
SPREADSHEET_ID = '1wkFZdvLvl3PAcP27EmAKaS_LQTvD1_lsRDko-4I3-LY'
RANGE_NAME = 'Responses_cgreplay_demo_2025!A:Q'  # Adjust range as needed

def is_synthetic(filename):
    """
    Determine if a video is synthetic based on its filename.
    
    Args:
        filename (str): The filename to check
        
    Returns:
        bool: True if the video is synthetic, False if real
    """
    # Videos with "interpolated" in the name are synthetic
    if "interpolated" in filename.lower():
        return True
    
    # Default to real if we can't determine
    return False

def authenticate_google_sheets():
    """
    Authenticate with Google Sheets API.
    
    Returns:
        service: The Google Sheets service object
    """
    try:
        # Try to use service account credentials if available
        if os.path.exists('credentials.json'):
            creds = service_account.Credentials.from_service_account_file(
                'credentials.json', 
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            return build('sheets', 'v4', credentials=creds)
        else:
            print("No credentials.json file found. Please follow the instructions below:")
            print("\n1. Go to https://console.cloud.google.com/")
            print("2. Create a new project or select an existing one")
            print("3. Enable the Google Sheets API")
            print("4. Create a service account and download the credentials as credentials.json")
            print("5. Share your Google Sheet with the service account email")
            print("\nAlternatively, you can manually download the data as CSV and use the --csv option.")
            sys.exit(1)
    except Exception as e:
        print(f"Error authenticating with Google Sheets API: {e}")
        sys.exit(1)

def get_data_from_google_sheets():
    """
    Fetch data from Google Sheets.
    
    Returns:
        pandas.DataFrame: The data from the Google Sheet
    """
    try:
        service = authenticate_google_sheets()
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print('No data found in the Google Sheet.')
            sys.exit(1)
            
        # Convert to DataFrame
        df = pd.DataFrame(values[1:], columns=values[0])
        return df
    except Exception as e:
        print(f"Error fetching data from Google Sheets: {e}")
        sys.exit(1)

def load_data_from_csv(csv_path):
    """
    Load data from a CSV file.
    
    Args:
        csv_path (str): Path to the CSV file
        
    Returns:
        pandas.DataFrame: The data from the CSV file
    """
    try:
        df = pd.read_csv(csv_path)
        return df
    except Exception as e:
        print(f"Error loading data from CSV: {e}")
        sys.exit(1)

def analyze_data(df):
    """
    Analyze the data to determine when users correctly identified synthetic videos.
    
    Args:
        df (pandas.DataFrame): The data to analyze
        
    Returns:
        dict: Analysis results
    """
    # Check if DataFrame is empty
    if df.empty:
        raise ValueError("DataFrame is empty")
    
    # Print debug info
    print(f"DataFrame shape: {df.shape}")
    print(f"DataFrame columns: {list(df.columns)}")
    
    # Ensure column names match the expected format
    expected_columns = [
        'Timestamp', 'User ID', 'Scene', 
        'Video A Filename', 'Video B Filename',
        'Video A Score', 'Video B Score',
        'Which Video Real'
    ]
    
    # Check if columns exist, with flexible matching
    column_mapping = {}
    for expected in expected_columns:
        expected_lower = expected.lower()
        found = False
        for col in df.columns:
            if expected_lower in col.lower() or col.lower() in expected_lower:
                column_mapping[expected] = col
                found = True
                break
        if not found:
            print(f"Warning: Could not find column matching '{expected}'")
    
    # Check if we have the minimum required columns
    required_columns = ['User ID', 'Video A Filename', 'Video B Filename', 'Which Video Real']
    missing_required = []
    for req_col in required_columns:
        if req_col not in column_mapping:
            missing_required.append(req_col)
    
    if missing_required:
        raise ValueError(f"Missing required columns: {missing_required}")
    
    # Create a copy of the dataframe with renamed columns
    df_work = df.copy()
    
    # Only rename columns that we found
    for expected, actual in column_mapping.items():
        if actual in df_work.columns:
            df_work = df_work.rename(columns={actual: expected})
    
    # Ensure we have the required columns after renaming
    for req_col in required_columns:
        if req_col not in df_work.columns:
            raise ValueError(f"Required column '{req_col}' not found after column mapping")
    
    # Clean the data - remove rows with NaN in critical columns
    df_work = df_work.dropna(subset=required_columns)
    
    if df_work.empty:
        raise ValueError("No valid data rows after cleaning")
    
    # Determine which videos are synthetic
    df_work['Video A Is Synthetic'] = df_work['Video A Filename'].apply(is_synthetic)
    df_work['Video B Is Synthetic'] = df_work['Video B Filename'].apply(is_synthetic)
    
    # Determine user's guess
    df_work['User Guess'] = df_work['Which Video Real'].apply(
        lambda x: {
            'a': 'Video A is Real',
            'b': 'Video B is Real',
            'both': 'Both are Real',
            'none': 'None are Real'
        }.get(str(x).lower(), 'Unknown')
    )
    
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
        else:  # a_synthetic and not b_synthetic
            return 'Video B is Real'
    
    df_work['Reality'] = df_work.apply(determine_reality, axis=1)
    
    # Determine if the user's guess was correct
    df_work['Correct Guess'] = df_work.apply(
        lambda row: row['User Guess'] == row['Reality'], axis=1
    )
    
    # Calculate overall accuracy
    overall_accuracy = df_work['Correct Guess'].mean()
    
    # Calculate accuracy by video type
    accuracy_by_type = {}
    for reality in df_work['Reality'].unique():
        subset = df_work[df_work['Reality'] == reality]
        if len(subset) > 0:
            accuracy = subset['Correct Guess'].mean()
            accuracy_by_type[reality] = accuracy
    
    # Calculate accuracy by user
    accuracy_by_user = df_work.groupby('User ID')['Correct Guess'].mean()
    
    # Calculate confusion matrix
    reality_categories = ['Video A is Real', 'Video B is Real', 'Both are Real', 'None are Real']
    
    # Create confusion matrix with proper handling of missing categories
    try:
        confusion_matrix = pd.crosstab(
            df_work['Reality'], 
            df_work['User Guess'],
            normalize='index'
        )
        
        # Ensure all categories are present in the confusion matrix
        for category in reality_categories:
            if category not in confusion_matrix.index:
                confusion_matrix.loc[category] = 0
            if category not in confusion_matrix.columns:
                confusion_matrix[category] = 0
        
        # Reorder rows and columns
        confusion_matrix = confusion_matrix.reindex(reality_categories, axis=0, fill_value=0)
        confusion_matrix = confusion_matrix.reindex(reality_categories, axis=1, fill_value=0)
    except Exception as e:
        print(f"Warning: Could not create confusion matrix: {e}")
        # Create empty confusion matrix as fallback
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

def generate_visualizations(results, output_dir='.'):
    """
    Generate visualizations from the analysis results.
    
    Args:
        results (dict): Analysis results
        output_dir (str): Directory to save visualizations
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Overall accuracy bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(['Correct', 'Incorrect'], 
            [results['overall_accuracy'], 1 - results['overall_accuracy']],
            color=['#2ecc71', '#e74c3c'],
            label=['Correct Identifications', 'Incorrect Identifications'])
    plt.title('Overall Accuracy in Identifying Real vs. Synthetic Videos', fontsize=16)
    plt.ylabel('Proportion of Responses', fontsize=14)
    plt.xlabel('User Response Accuracy', fontsize=14)
    plt.ylim(0, 1)
    plt.text(0, results['overall_accuracy'] + 0.02, 
             f"{results['overall_accuracy']:.2%}", 
             ha='center', fontsize=12)
    plt.text(1, (1 - results['overall_accuracy']) + 0.02, 
             f"{1 - results['overall_accuracy']:.2%}", 
             ha='center', fontsize=12)
    
    # Add a legend to explain the color coding
    handles = [
        plt.Rectangle((0,0),1,1, color='#2ecc71'),
        plt.Rectangle((0,0),1,1, color='#e74c3c')
    ]
    plt.legend(handles, ['Correct Identifications', 'Incorrect Identifications'], 
               title='Response Accuracy', loc='upper right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'overall_accuracy.png'), dpi=300)
    
    # 2. Accuracy by video type
    plt.figure(figsize=(12, 6))
    video_types = list(results['accuracy_by_type'].keys())
    accuracies = list(results['accuracy_by_type'].values())
    
    # Sort by accuracy
    sorted_indices = np.argsort(accuracies)[::-1]
    video_types = [video_types[i] for i in sorted_indices]
    accuracies = [accuracies[i] for i in sorted_indices]
    
    # Add a more descriptive title and labels
    bars = plt.bar(video_types, accuracies, color='#3498db', 
                  label='Accuracy Rate')
    plt.title('Accuracy by Video Type: User Ability to Identify Real vs. Synthetic Videos', fontsize=16)
    plt.ylabel('Accuracy Rate', fontsize=14)
    plt.xlabel('Video Scenario', fontsize=14)
    plt.ylim(0, 1)
    plt.xticks(rotation=45, ha='right')
    
    # Add accuracy values on top of bars
    for i, bar in enumerate(bars):
        plt.text(bar.get_x() + bar.get_width()/2, 
                 bar.get_height() + 0.02, 
                 f"{accuracies[i]:.2%}", 
                 ha='center', fontsize=12)
    
    # Add a legend to explain the bars
    plt.legend(loc='lower left')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'accuracy_by_type.png'), dpi=300)
    
    # 3. Confusion matrix heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(results['confusion_matrix'], annot=True, cmap='Blues', fmt='.2%',
                cbar_kws={'label': 'Proportion of Responses'})
    plt.title('Confusion Matrix: Actual Video Reality vs. User Guess', fontsize=16)
    plt.ylabel('Actual Reality (Ground Truth)', fontsize=14)
    plt.xlabel('User Guess (Perceived Reality)', fontsize=14)
    
    # Add a text annotation
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'confusion_matrix.png'), dpi=300)
    
    # 4. Distribution of user accuracy
    plt.figure(figsize=(10, 6))
    # Create the histogram with KDE and explicitly label the KDE curve
    ax = sns.histplot(results['accuracy_by_user'], bins=10, kde=True, color='#9b59b6')
    # Get the line objects from the axes
    lines = ax.get_lines()
    # The first line should be the KDE curve
    if lines:
        # Set the label for the KDE curve
        lines[0].set_label('Density Estimation (KDE)')
    
    plt.title('Distribution of User Accuracy', fontsize=16)
    plt.xlabel('Accuracy', fontsize=14)
    plt.ylabel('Number of Users', fontsize=14)
    plt.axvline(results['overall_accuracy'], color='red', linestyle='--', 
                label=f'Overall Accuracy: {results["overall_accuracy"]:.2%}')
    # Add a more descriptive legend that explains all elements
    plt.legend(title='Legend', loc='best')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'user_accuracy_distribution.png'), dpi=300)
    
    print(f"Visualizations saved to {output_dir}")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze QoE data and generate visualizations.')
    parser.add_argument('--csv', type=str, help='Path to CSV file with QoE data')
    parser.add_argument('--output', type=str, default='visualizations', 
                        help='Directory to save visualizations')
    args = parser.parse_args()
    
    print("QoE Data Analysis")
    print("----------------")
    
    # Get data
    if args.csv:
        print(f"Loading data from CSV: {args.csv}")
        df = load_data_from_csv(args.csv)
    else:
        print("Fetching data from Google Sheets...")
        df = get_data_from_google_sheets()
    
    print(f"Loaded {len(df)} records")
    
    # Analyze data
    print("Analyzing data...")
    results = analyze_data(df)
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print(f"Overall accuracy: {results['overall_accuracy']:.2%}")
    print("\nAccuracy by video type:")
    for video_type, accuracy in results['accuracy_by_type'].items():
        print(f"  {video_type}: {accuracy:.2%}")
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    generate_visualizations(results, args.output)
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()
