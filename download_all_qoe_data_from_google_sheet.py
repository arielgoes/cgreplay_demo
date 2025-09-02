#!/usr/bin/env python3
"""
QoE Data Downloader

This script downloads data from the Google Sheet containing subjective QoE assessment results
and saves it as a CSV file for offline analysis.
"""

import os
import sys
import pandas as pd
import requests
import csv
from io import StringIO

# Constants
SHEET_URL = "https://docs.google.com/spreadsheets/d/1wkFZdvLvl3PAcP27EmAKaS_LQTvD1_lsRDko-4I3-LY/export?format=csv&gid=625363607"
OUTPUT_FILE = "all_qoe_data_from_google_sheet.csv"

def download_sheet_as_csv(url, output_file):
    """
    Download a Google Sheet as CSV.
    
    Args:
        url (str): URL to the Google Sheet export
        output_file (str): Path to save the CSV file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Downloading data from Google Sheet...")
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Save the CSV content to a file
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            f.write(response.text)
        
        # Verify the file was created and has content
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"Data successfully saved to {output_file}")
            
            # Count rows in the CSV file
            with open(output_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                row_count = sum(1 for row in reader) - 1  # Subtract 1 for header
            
            print(f"Downloaded {row_count} records")
            return True
        else:
            print(f"Error: Failed to save data to {output_file}")
            return False
    
    except requests.exceptions.RequestException as e:
        print(f"Error downloading data: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download QoE data from Google Sheet.')
    parser.add_argument('--output', type=str, default=OUTPUT_FILE, 
                        help=f'Output CSV file (default: {OUTPUT_FILE})')
    args = parser.parse_args()
    
    print("QoE Data Downloader")
    print("------------------")
    
    success = download_sheet_as_csv(SHEET_URL, args.output)
    
    if success:
        print("\nNext steps:")
        print(f"1. Run the analysis script: python analyze_all_qoe_data_from_google_sheet.py --csv {args.output}")
        print("2. Check the 'visualizations' directory for the generated graphs")
    else:
        print("\nDownload failed. Please try again or manually download the data from:")
        print("https://docs.google.com/spreadsheets/d/1wkFZdvLvl3PAcP27EmAKaS_LQTvD1_lsRDko-4I3-LY/edit?gid=625363607")
        print("Save it as a CSV file and then run: python analyze_all_qoe_data_from_google_sheet.py --csv your_file.csv")

if __name__ == "__main__":
    main()
