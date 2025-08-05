#!/usr/bin/env python3
"""
Quick test script to verify Vercel deployment is working
"""

import requests
import json
import sys

def test_vercel_endpoint(url, endpoint):
    """Test a specific endpoint"""
    full_url = f"{url}{endpoint}"
    
    try:
        print(f"Testing: {full_url}")
        response = requests.get(full_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {endpoint}: SUCCESS")
            
            # Show key information
            if endpoint == "/api/test":
                print(f"   Database: {data.get('database', {}).get('status', 'unknown')}")
                print(f"   Text Files: {data.get('text_files', {}).get('status', 'unknown')}")
            elif endpoint == "/api/documents":
                print(f"   Documents: {data.get('count', 0)}")
                print(f"   Architecture: {data.get('architecture', 'unknown')}")
            elif "/content" in endpoint:
                print(f"   Title: {data.get('data', {}).get('titulo', 'unknown')}")
                print(f"   Architecture: {data.get('data', {}).get('architecture', 'unknown')}")
                print(f"   Word Count: {data.get('data', {}).get('word_count', 0)}")
            
            return True
        else:
            print(f"❌ {endpoint}: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏰ {endpoint}: TIMEOUT (>30s)")
        return False
    except Exception as e:
        print(f"❌ {endpoint}: ERROR - {str(e)}")
        return False

def main():
    # Vercel URL (replace with your actual URL)
    VERCEL_URL = "https://matriz-legal-iso-27001.vercel.app"
    
    print("🚀 Testing Vercel Deployment...")
    print(f"Base URL: {VERCEL_URL}")
    print("=" * 50)
    
    # Test endpoints
    endpoints = [
        "/api/test",
        "/api/documents", 
        "/api/documents/ley_1581_2012/content",
        "/api/stats"
    ]
    
    results = []
    for endpoint in endpoints:
        success = test_vercel_endpoint(VERCEL_URL, endpoint)
        results.append(success)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Vercel deployment is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())