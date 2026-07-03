"""
ARGOS Benchmark Script - LFW Dataset Testing
Tests facial recognition accuracy using Labeled Faces in the Wild dataset

Usage: python benchmark_lfw.py
"""

import os
import base64
import requests
import time
from pathlib import Path
from typing import List, Dict, Tuple

# Configuration
ARGOS_URL = "http://localhost:5000"
LFW_PATH = r"C:\Users\desarrollo\Documents\ICARUSDB_DEV\archive\lfw-deepfunneled\lfw-deepfunneled"
NUM_PERSONS = 10  # Number of persons to test
MIN_PHOTOS = 2    # Minimum photos per person


def get_persons_with_multiple_photos(lfw_path: str, min_photos: int = 2, limit: int = 10) -> List[Dict]:
    """Find persons with at least min_photos images"""
    persons = []
    for person_dir in Path(lfw_path).iterdir():
        if person_dir.is_dir():
            photos = list(person_dir.glob("*.jpg"))
            if len(photos) >= min_photos:
                persons.append({
                    "name": person_dir.name,
                    "photos": [str(p) for p in photos[:min_photos]]  # Take first N photos
                })
                if len(persons) >= limit:
                    break
    return persons


def image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_embedding(image_base64: str) -> List[float]:
    """Extract facial embedding via ARGOS API"""
    response = requests.post(
        f"{ARGOS_URL}/api/extract-embedding",
        json={"image": image_base64},
        timeout=60
    )
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            return data.get("embedding", [])
    return []


def compare_embeddings(embedding1: List[float], embedding2: List[float]) -> Dict:
    """Compare two embeddings via ARGOS API"""
    response = requests.post(
        f"{ARGOS_URL}/api/compare-embeddings",
        json={
            "embedding1": embedding1,
            "embedding2": embedding2
        },
        timeout=30
    )
    if response.status_code == 200:
        return response.json()
    return {"success": False, "error": "API call failed"}


def run_verification_test(persons: List[Dict]) -> Dict:
    """
    Test 1: Same person verification (should match)
    Compare photo1 vs photo2 of same person
    """
    print("\n" + "="*60)
    print("TEST 1: Same Person Verification (True Positives)")
    print("="*60)
    
    results = []
    for person in persons:
        print(f"\n→ Testing: {person['name']}")
        
        # Extract embeddings for both photos
        emb1 = extract_embedding(image_to_base64(person["photos"][0]))
        emb2 = extract_embedding(image_to_base64(person["photos"][1]))
        
        if not emb1 or not emb2:
            print(f"  ❌ Failed to extract embeddings")
            continue
        
        # Compare
        comparison = compare_embeddings(emb1, emb2)
        
        if comparison.get("success"):
            verified = comparison.get("verified", False)
            similarity = comparison.get("similarity_percent", 0)
            distance = comparison.get("distance", 1)
            
            status = "✅ PASS" if verified else "❌ FAIL"
            print(f"  {status} | Similarity: {similarity:.2f}% | Distance: {distance:.4f}")
            
            results.append({
                "name": person["name"],
                "verified": verified,
                "similarity": similarity,
                "distance": distance
            })
        else:
            print(f"  ❌ Comparison failed: {comparison.get('error')}")
    
    # Summary
    passed = sum(1 for r in results if r["verified"])
    total = len(results)
    avg_similarity = sum(r["similarity"] for r in results) / total if total > 0 else 0
    
    print(f"\n📊 Same Person Results: {passed}/{total} correct ({passed/total*100:.1f}%)")
    print(f"📊 Average Similarity: {avg_similarity:.2f}%")
    
    return {
        "test": "same_person",
        "passed": passed,
        "total": total,
        "accuracy": passed/total if total > 0 else 0,
        "avg_similarity": avg_similarity,
        "results": results
    }


def run_different_person_test(persons: List[Dict]) -> Dict:
    """
    Test 2: Different person verification (should NOT match)
    Compare person1.photo1 vs person2.photo1
    """
    print("\n" + "="*60)
    print("TEST 2: Different Person Verification (True Negatives)")
    print("="*60)
    
    results = []
    embeddings = {}
    
    # First, extract embeddings for first photo of each person
    print("\n→ Extracting embeddings...")
    for person in persons:
        emb = extract_embedding(image_to_base64(person["photos"][0]))
        if emb:
            embeddings[person["name"]] = emb
    
    # Compare each pair of different persons
    names = list(embeddings.keys())
    comparisons_made = 0
    max_comparisons = 15  # Limit comparisons
    
    for i, name1 in enumerate(names):
        for name2 in names[i+1:]:
            if comparisons_made >= max_comparisons:
                break
                
            comparison = compare_embeddings(embeddings[name1], embeddings[name2])
            
            if comparison.get("success"):
                verified = comparison.get("verified", False)
                similarity = comparison.get("similarity_percent", 0)
                
                # For different persons, verified=False is correct
                is_correct = not verified
                status = "✅ PASS" if is_correct else "❌ FAIL (False Positive!)"
                
                print(f"  {name1} vs {name2}: {status} | Similarity: {similarity:.2f}%")
                
                results.append({
                    "pair": f"{name1} vs {name2}",
                    "verified": verified,
                    "correct": is_correct,
                    "similarity": similarity
                })
                comparisons_made += 1
        
        if comparisons_made >= max_comparisons:
            break
    
    # Summary
    passed = sum(1 for r in results if r["correct"])
    total = len(results)
    false_positives = sum(1 for r in results if r["verified"])
    
    print(f"\n📊 Different Person Results: {passed}/{total} correct ({passed/total*100:.1f}%)")
    print(f"⚠️  False Positives: {false_positives}")
    
    return {
        "test": "different_person",
        "passed": passed,
        "total": total,
        "accuracy": passed/total if total > 0 else 0,
        "false_positives": false_positives,
        "results": results
    }


def main():
    print("\n" + "🔬 "*20)
    print("      ARGOS BENCHMARK - LFW Dataset Test")
    print("🔬 "*20)
    
    # Check ARGOS connectivity
    print(f"\n→ Checking ARGOS at {ARGOS_URL}...")
    try:
        health = requests.get(f"{ARGOS_URL}/health", timeout=5)
        if health.status_code == 200:
            print("  ✅ ARGOS is running")
        else:
            print("  ❌ ARGOS not responding correctly")
            return
    except Exception as e:
        print(f"  ❌ Cannot connect to ARGOS: {e}")
        return
    
    # Get test persons
    print(f"\n→ Loading {NUM_PERSONS} persons from LFW dataset...")
    persons = get_persons_with_multiple_photos(LFW_PATH, MIN_PHOTOS, NUM_PERSONS)
    print(f"  Found {len(persons)} persons with {MIN_PHOTOS}+ photos")
    
    if not persons:
        print("  ❌ No valid persons found")
        return
    
    # Run tests
    start_time = time.time()
    
    same_person_results = run_verification_test(persons)
    different_person_results = run_different_person_test(persons)
    
    elapsed = time.time() - start_time
    
    # Final summary
    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)
    print(f"\n✅ Same Person Accuracy (TAR):     {same_person_results['accuracy']*100:.1f}%")
    print(f"✅ Different Person Accuracy (TNR): {different_person_results['accuracy']*100:.1f}%")
    print(f"⚠️  False Acceptance Rate (FAR):   {different_person_results['false_positives']}/{different_person_results['total']}")
    print(f"\n⏱️  Total time: {elapsed:.1f} seconds")
    print(f"📊 Avg similarity (same person): {same_person_results['avg_similarity']:.2f}%")


if __name__ == "__main__":
    main()
