"""
Test script for the /api/financials endpoint
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_financials_endpoint():
    """Test the /api/financials endpoint with different parameters"""
    
    test_cases = [
        {
            "name": "IBM Income Statement - Quarterly",
            "params": {"company": "IBM", "type": "IS", "period": "quarterly"}
        },
        {
            "name": "IBM Income Statement - Annual",
            "params": {"company": "IBM", "type": "IS", "period": "annual"}
        },
        {
            "name": "IBM Balance Sheet - Quarterly",
            "params": {"company": "IBM", "type": "BS", "period": "quarterly"}
        },
        {
            "name": "IBM Cash Flow - Quarterly",
            "params": {"company": "IBM", "type": "CF", "period": "quarterly"}
        }
    ]
    
    print("=" * 80)
    print("Testing /api/financials endpoint")
    print("=" * 80)
    
    for test in test_cases:
        print(f"\n🧪 Test: {test['name']}")
        print(f"   Parameters: {test['params']}")
        
        try:
            response = requests.get(f"{BASE_URL}/api/financials", params=test['params'])
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Status: {response.status_code}")
                print(f"   Company: {data.get('company')}")
                print(f"   Type: {data.get('type')}")
                print(f"   Period: {data.get('period')}")
                print(f"   Periods available: {len(data.get('periods', []))}")
                print(f"   First 3 periods: {data.get('periods', [])[:3]}")
                print(f"   Number of line items: {len(data.get('data', {}))}")
                
                # Show sample data
                if data.get('data'):
                    first_item = list(data['data'].keys())[0]
                    print(f"   Sample item '{first_item}': {data['data'][first_item]}")
            else:
                print(f"   ❌ Status: {response.status_code}")
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 80)

def test_invalid_parameters():
    """Test with invalid parameters"""
    print("\n🧪 Testing invalid parameters...")
    
    invalid_tests = [
        {"company": "IBM", "type": "INVALID", "period": "quarterly"},
        {"company": "IBM", "type": "IS", "period": "invalid_period"},
        {"company": "NONEXISTENT", "type": "IS", "period": "quarterly"}
    ]
    
    for params in invalid_tests:
        print(f"\n   Testing: {params}")
        response = requests.get(f"{BASE_URL}/api/financials", params=params)
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Expected error: {response.json().get('detail')}")

if __name__ == "__main__":
    print("\n⚠️  Make sure the FastAPI server is running on http://localhost:8000")
    print("⚠️  Make sure you have imported financial data using data.py\n")
    
    input("Press Enter to start tests...")
    
    test_financials_endpoint()
    test_invalid_parameters()
    
    print("\n✅ Tests completed!")
