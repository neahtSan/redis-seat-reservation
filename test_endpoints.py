#!/usr/bin/env python3
"""
Test script to verify the seat reservation endpoints work correctly
and only return SUCCESS (200/201) and CONFLICT (409) status codes.
"""
import requests
import json
import time

BASE_URL = "http://localhost:3000"

def test_endpoint(method, url, data=None, expected_status_codes=None):
    """Test an endpoint and verify it returns expected status codes"""
    if expected_status_codes is None:
        expected_status_codes = [200, 201, 409]
    
    try:
        if method.upper() == 'POST':
            response = requests.post(url, json=data, timeout=10)
        else:
            response = requests.get(url, timeout=10)
        
        print(f"{method} {url}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code in expected_status_codes:
            print("✅ Status code is as expected")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            
        print("-" * 50)
        return response.status_code
        
    except requests.exceptions.RequestException as e:
        print(f"🚨 Request failed: {e}")
        return 0

def main():
    print("🚀 Testing Seat Reservation Endpoints")
    print("=" * 50)
    
    # Test 1: Initialize seats
    print("1. Initialize seats")
    test_endpoint("POST", f"{BASE_URL}/initialize")
    
    # Test 2: Check overall availability
    print("2. Check all seats availability")
    test_endpoint("GET", f"{BASE_URL}/availability/check-all")
    
    # Test 3: Check specific zone/row occupancy
    print("3. Check zone 1, row 1 occupancy")
    test_endpoint("GET", f"{BASE_URL}/occupancy/1/1")
    
    # Test 4: Reserve some seats
    print("4. Reserve 2 seats in zone 1, row 1")
    test_endpoint("POST", f"{BASE_URL}/reserve", {
        "zone": 1,
        "row": 1,
        "count": 2
    })
    
    # Test 5: Check occupancy after reservation
    print("5. Check zone 1, row 1 occupancy after reservation")
    test_endpoint("GET", f"{BASE_URL}/occupancy/1/1")
    
    # Test 6: Try to reserve with invalid input (should return 409)
    print("6. Try invalid reservation (should get CONFLICT)")
    test_endpoint("POST", f"{BASE_URL}/reserve", {
        "zone": 99,  # Invalid zone
        "row": 1,
        "count": 2
    })
    
    # Test 7: Get Redis stats
    print("7. Get Redis stats")
    test_endpoint("GET", f"{BASE_URL}/stats")
    
    print("🏁 Testing complete!")

if __name__ == "__main__":
    main()
