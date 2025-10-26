"""
Script test đơn giản cho API
"""
import requests
import json

def test_api():
    base_url = "http://localhost:8000"
    
    print("=" * 80)
    print("TEST API FINANCIALS ENDPOINT")
    print("=" * 80)
    
    # Test 1: Income Statement - Quarterly
    print("\n📊 Test 1: Income Statement - Quarterly (IBM)")
    print("-" * 80)
    
    try:
        response = requests.get(
            f"{base_url}/api/financials",
            params={
                "company": "IBM",
                "type": "IS",
                "period": "quarterly"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Company: {data.get('company')}")
            print(f"✅ Type: {data.get('type')}")
            print(f"✅ Period: {data.get('period')}")
            print(f"✅ Number of periods: {len(data.get('periods', []))}")
            print(f"✅ Number of line items: {len(data.get('data', {}))}")
            print(f"\n📝 First 5 periods: {data.get('periods', [])[:5]}")
            print(f"📝 First 3 line items:")
            for i, item_name in enumerate(list(data.get('data', {}).keys())[:3]):
                print(f"   {i+1}. {item_name}")
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Không thể kết nối đến server!")
        print("📝 Hãy đảm bảo server đang chạy:")
        print("   python fastapi_server.py")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    
    # Test 2: Balance Sheet - Annual
    print("\n📊 Test 2: Balance Sheet - Annual (IBM)")
    print("-" * 80)
    
    try:
        response = requests.get(
            f"{base_url}/api/financials",
            params={
                "company": "IBM",
                "type": "BS",
                "period": "annual"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Number of periods: {len(data.get('periods', []))}")
            print(f"✅ Number of line items: {len(data.get('data', {}))}")
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    
    # Test 3: Cash Flow - Quarterly
    print("\n📊 Test 3: Cash Flow - Quarterly (IBM)")
    print("-" * 80)
    
    try:
        response = requests.get(
            f"{base_url}/api/financials",
            params={
                "company": "IBM",
                "type": "CF",
                "period": "quarterly"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Number of periods: {len(data.get('periods', []))}")
            print(f"✅ Number of line items: {len(data.get('data', {}))}")
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    
    print("\n" + "=" * 80)
    print("✅ TEST HOÀN TẤT")
    print("=" * 80)

if __name__ == "__main__":
    test_api()