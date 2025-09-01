#!/usr/bin/env python3
"""
Video Pair Reproducer for cgreplay_demo

This script reproduces the exact same video pairs shown to a specific user during evaluation,
based on their user ID. It uses the same deterministic algorithms as the frontend for complete
reproducibility.

IMPORTANT: Do not modify the following functions as they must match the JavaScript implementation:
- hash_string_to_seed()
- seeded_random()
- select_random_pairs_with_seed()

These functions ensure exact reproduction of the video pairs shown to users.

Usage:
    python retrieve_videos_from_user_hash_id.py <user_id>
"""

import argparse
import json
import csv
import os
from collections import defaultdict

def hash_string_to_seed(s):
    """Convert a string to a 32-bit unsigned integer seed, matching JavaScript."""
    hash_ = 5381
    for c in s:
        # JS: hash = ((hash << 5) + hash) + c, all in 32-bit unsigned
        hash_ = ((hash_ << 5) + hash_ + ord(c)) & 0xFFFFFFFF
    return hash_

def seeded_random(seed):
    """Create a seeded random number generator, matching JavaScript's behavior."""
    state = seed & 0xFFFFFFFF  # force 32-bit unsigned
    while True:
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF  # force 32-bit unsigned
        yield state / 4294967296

def select_random_pairs_with_seed(pairs, count, seed):
    """Select a random subset of pairs using a deterministic seed, matching JavaScript."""
    pairs_copy = pairs[:]
    selected = []
    rand_gen = seeded_random(seed)
    count = min(count, len(pairs_copy))
    for _ in range(count):
        idx = int(next(rand_gen) * len(pairs_copy))
        selected.append(pairs_copy.pop(idx))
    return selected

def get_video_list_hash(videos):
    """Create a deterministic hash of the video list for versioning."""
    video_str = json.dumps(videos, sort_keys=True)
    return hash_string_to_seed(video_str)

import json

def load_user_pairs_from_csv(user_id, filepath='qoe_data.csv'):
    """Load video pairs for a specific user from the QoE data CSV file."""
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found. Please run download_qoe_data.py first.")
        return None, None
    
    try:
        pairs = []
        metadata = defaultdict(str)
        seen_scenes = set()  # Track scenes we've already processed to avoid duplicates
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['User ID'] == user_id:
                    # Extract metadata from the first matching row
                    if not metadata['version']:
                        metadata = {
                            'version': row.get('Video List Version', 'unknown'),
                            'hash': row.get('Video List Hash', 'unknown'),
                            'timestamp': row.get('Video List Timestamp', 'unknown')
                        }
                    
                    # Create a pair object
                    scene = row.get('Scene', 'Unknown')
                    
                    # Skip if we've already seen this scene (to avoid duplicates)
                    if scene in seen_scenes:
                        continue
                    
                    pair = {
                        'scene': scene,
                        'videoA': row.get('Video A Filename', ''),
                        'videoB': row.get('Video B Filename', ''),
                        'scoreA': row.get('Video A Score', ''),
                        'scoreB': row.get('Video B Score', '')
                    }
                    
                    # Only add if both videos are specified
                    if pair['videoA'] and pair['videoB']:
                        pairs.append(pair)
                        seen_scenes.add(scene)  # Mark this scene as processed
        
        if pairs:
            print(f"Loaded {len(pairs)} pairs for user {user_id} from {filepath}")
            return pairs, metadata
        else:
            print(f"No data found for user {user_id} in {filepath}")
            return None, None
            
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None, None

def generate_pairs_for_user(user_id, videos):
    """Generate the exact video pairs shown to a user during their session."""
    user_seed = hash_string_to_seed(user_id)
    
    # COMBINATION GENERATION (not permutations):
    # This function generates all possible unique video combinations where each pair (A,B) 
    # appears exactly once. We use combinations rather than permutations because:
    # 1. Eliminates redundancy - no need for both (VideoX, VideoY) and (VideoY, VideoX)
    # 2. Reduces cognitive load on users by avoiding duplicate comparisons
    # 3. Maximizes coverage of unique video relationships within limited evaluation time
    # 4. Ensures scientific rigor by preventing bias from repeated pair presentations
    #
    # The nested loop with j = i + 1 ensures we only generate combinations:
    # For videos [A, B, C], we get: (A,B), (A,C), (B,C) - exactly C(n,2) = n*(n-1)/2 pairs
    # This MUST match the JavaScript implementation in index.html for reproducibility.
    
    all_pairs = []
    for i in range(len(videos)):
        for j in range(i + 1, len(videos)):
            all_pairs.append({
                "scene": f"Pair {len(all_pairs) + 1}",
                "videoA": videos[i],
                "videoB": videos[j]
            })
    
    # Select pairs using the same algorithm as the frontend
    selected_pairs = select_random_pairs_with_seed(all_pairs, 5, user_seed)
    
    # Apply the videoA/videoB swap logic for each pair
    result_pairs = []
    for idx, pair in enumerate(selected_pairs):
        pair_seed = user_seed + idx
        rand = seeded_random(pair_seed)
        swap = next(rand) >= 0.5
        
        if swap:
            result_pairs.append({
                "scene": pair["scene"],
                "videoA": pair["videoB"],
                "videoB": pair["videoA"],
                "swapped": True
            })
        else:
            result_pairs.append({
                "scene": pair["scene"],
                "videoA": pair["videoA"],
                "videoB": pair["videoB"],
                "swapped": False
            })
    
    return result_pairs

def validate_against_known_session(user_id, expected_pairs, videos):
    """Verify script output matches expected pairs from a real session."""
    generated_pairs = generate_pairs_for_user(user_id, videos)
    
    # Compare each pair
    for i, (gen, exp) in enumerate(zip(generated_pairs, expected_pairs)):
        if gen["scene"] != exp["scene"] or gen["videoA"] != exp["videoA"] or gen["videoB"] != exp["videoB"]:
            print(f"❌ Mismatch in pair {i+1}:")
            print(f"  Generated: {gen['scene']} - {gen['videoA']} vs {gen['videoB']}")
            print(f"  Expected:  {exp['scene']} - {exp['videoA']} vs {exp['videoB']}")
            return False
    
    print(f"✅ All pairs match for user {user_id}")
    return True

def output_csv(pairs, filename=None):
    """Output pairs as CSV format, either to file or stdout."""
    lines = ["Scene,VideoA,VideoB"]
    for pair in pairs:
        lines.append(f"{pair['scene']},{pair['videoA']},{pair['videoB']}")
    
    csv_output = "\n".join(lines)
    
    if filename:
        with open(filename, 'w') as f:
            f.write(csv_output)
        print(f"Saved pairs to {filename}")
    else:
        return csv_output

# Known pairs from the spreadsheet data
KNOWN_PAIRS = {
    "ADBKIeixrc": [
        {"scene": "Pair 27", "videoA": "videos/video_with_degrad_mk11_1080p.mp4", "videoB": "videos/original_video_1280_720.mp4"},
        {"scene": "Pair 6", "videoA": "videos/original_video_upsampled_from_1280_720_to_1920_1080.mp4", "videoB": "videos/TEMP_TEST.mp4"}
    ],
    "NmxkPu7tqf": [
        {"scene": "Pair 10", "videoA": "videos/interpolated_rife_1280_720_30fps.mp4", "videoB": "videos/original_video.mp4"}
    ]
}

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrieve video pairs for a given user ID.")
    parser.add_argument("user_id", type=str, help="User ID to reproduce video pairs for")
    parser.add_argument("--csv", action="store_true", help="Output in CSV format")
    parser.add_argument("--save", type=str, help="Save output to file")
    parser.add_argument("--generate", action="store_true", help="Generate pairs algorithmically instead of using CSV data")
    args = parser.parse_args()
    
    # First try to load pairs directly from CSV
    pairs = None
    metadata = None
    
    if not args.generate:
        pairs, metadata = load_user_pairs_from_csv(args.user_id)
    
    # If no pairs found in CSV or --generate flag is used, fall back to algorithmic generation
    if pairs is None or args.generate:
        print("Falling back to algorithmic pair generation...")
        
        # Load video list from JSON
        try:
            with open('video_list.json', 'r') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and "files" in data:
                videos = data["files"]
                metadata = {
                    "version": data.get("version", "unknown"),
                    "hash": data.get("hash", "unknown"),
                    "timestamp": data.get("generated_at", "unknown")
                }
                print(f"Loaded {len(videos)} videos from video_list.json")
            else:
                raise ValueError("Unexpected JSON structure in video list file")
                
        except Exception as e:
            print(f"Error loading video_list.json: {e}")
            # Fallback to hardcoded list
            videos = [
                "videos/TEMP_TEST.mp4",
                "videos/interpolated_rife_1280_720_30fps.mp4",
                "videos/interpolated_video_addWeighted.mp4",
                "videos/interpolated_video_film.mp4",
                "videos/original_video.mp4",
                "videos/original_video_1280_720.mp4",
                "videos/original_video_upsampled_from_1280_720_to_1920_1080.mp4",
                "videos/video_with_degrad_mk11_1080p.mp4"
            ]
            metadata = {"version": "unknown", "hash": "unknown", "timestamp": "unknown"}
            print(f"Using fallback list with {len(videos)} videos")
        
        # Generate pairs algorithmically
        pairs = generate_pairs_for_user(args.user_id, videos)
    
    # Output
    print(f"\nUser ID: {args.user_id}")
    if metadata:
        print(f"Video list version: {metadata['version']}")
        print(f"Video list hash: {metadata['hash']}")
    
    if args.csv:
        if args.save:
            output_csv(pairs, args.save)
        else:
            print(output_csv(pairs))
    else:
        # Default tab-separated output
        print(f"\n{'Scene':<10}\t{'VideoA':<50}\t{'VideoB':<50}")
        print("-" * 110)
        for pair in pairs:
            print(f"{pair['scene']:<10}\t{pair['videoA']:<50}\t{pair['videoB']:<50}")
