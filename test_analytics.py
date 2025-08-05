#!/usr/bin/env python3
"""
Test script to generate analytics data for the monitoring dashboard
"""

import requests
import time
import random
import json

BASE_URL = "http://localhost:5002"
ADMIN_TOKEN = "admin_daniel_2024"

def test_endpoints():
    """Simulate user activity to generate analytics data"""
    
    print("🧪 Testing Analytics System...")
    
    # Test basic endpoints
    endpoints_to_test = [
        "/api/test",
        "/api/documents",
        "/api/stats"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"✅ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")
    
    # Test chat endpoint with different queries
    chat_queries = [
        "¿Qué es la Ley 1581 de 2012?",
        "Decreto 1072 artículo 5",
        "Protección de datos personales",
        "ISO 27001 implementación",
        "¿Cuáles son las obligaciones del responsable?"
    ]
    
    print("\n🤖 Testing Chat Queries...")
    for query in chat_queries:
        try:
            response = requests.post(f"{BASE_URL}/api/chat", 
                json={"query": query})
            print(f"✅ Chat query: {response.status_code}")
            time.sleep(1)  # Simulate real user behavior
        except Exception as e:
            print(f"❌ Chat query error: {e}")
    
    # Test document access
    print("\n📄 Testing Document Access...")
    try:
        # Get list of documents first
        docs_response = requests.get(f"{BASE_URL}/api/documents")
        if docs_response.status_code == 200:
            docs_data = docs_response.json()
            if docs_data.get('success') and docs_data.get('data'):
                # Access a few random documents
                documents = docs_data['data'][:5]  # First 5 documents
                for doc in documents:
                    doc_id = doc.get('nombre_archivo')
                    if doc_id:
                        response = requests.get(f"{BASE_URL}/api/documents/{doc_id}/content")
                        print(f"✅ Document access {doc_id}: {response.status_code}")
                        time.sleep(0.5)
    except Exception as e:
        print(f"❌ Document access error: {e}")
    
    print("\n📊 Testing Admin Analytics...")
    
    # Test admin endpoints
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    
    admin_endpoints = [
        "/api/admin/analytics/overview",
        "/api/admin/analytics/sessions", 
        "/api/admin/analytics/performance",
        "/api/admin/analytics/chat",
        "/api/admin/analytics/documents",
        "/api/admin/analytics/realtime"
    ]
    
    for endpoint in admin_endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}?hours=24", headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint}: Success")
                if endpoint == "/api/admin/analytics/overview":
                    # Print some key metrics
                    overview = data.get('data', {})
                    sessions = overview.get('sessions', {})
                    queries = overview.get('chat_queries', {})
                    print(f"   📈 Sessions: {sessions.get('total', 0)} total, {sessions.get('recent', 0)} recent")
                    print(f"   💬 Queries: {queries.get('total', 0)} total, {queries.get('recent', 0)} recent")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")
    
    print("\n🎯 Analytics test completed!")
    print(f"🌐 Admin Dashboard available at: {BASE_URL}/admin")
    print(f"🔑 Use token: {ADMIN_TOKEN}")

if __name__ == "__main__":
    # Wait a bit for server to fully start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    test_endpoints()