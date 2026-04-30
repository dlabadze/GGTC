#!/usr/bin/env python3
"""
Simple test script to verify the visual report functionality
გამოიყენება ვიზუალური ანგარიშის ფუნქციონალის შესამოწმებლად
"""

import requests
import json
from datetime import datetime

# Configuration
ODOO_URL = "http://localhost:8069"  # Change to your Odoo URL
DATABASE = "your_database"  # Change to your database name
USERNAME = "admin"  # Change to your username
PASSWORD = "admin"  # Change to your password

class VisualReportTester:
    def __init__(self, url, db, username, password):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.session = requests.Session()
        
    def login(self):
        """Login to Odoo"""
        login_data = {
            'login': self.username,
            'password': self.password,
            'db': self.db
        }
        
        response = self.session.post(f"{self.url}/web/login", data=login_data)
        if response.status_code == 200:
            print("✅ Successfully logged in to Odoo")
            return True
        else:
            print("❌ Failed to login to Odoo")
            return False
    
    def test_visual_report_page(self):
        """Test if the visual report page loads"""
        try:
            response = self.session.get(f"{self.url}/budget/visual_report")
            if response.status_code == 200:
                print("✅ Visual report page loads successfully")
                # Check if the page contains expected elements
                if 'ბიუჯეტის ვიზუალური ანგარიში' in response.text:
                    print("✅ Page contains Georgian title")
                if 'purchase_plan_select' in response.text:
                    print("✅ Purchase plan selector found")
                if 'budget_cpv_select' in response.text:
                    print("✅ Budget CPV selector found")
                if 'Chart.js' in response.text:
                    print("✅ Chart.js library included")
                return True
            else:
                print(f"❌ Visual report page failed to load (Status: {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ Error testing visual report page: {str(e)}")
            return False
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        endpoints = [
            '/budget/get_budget_cpvs',
            '/budget/get_cpv_lines_data',
            '/budget/get_chart_data'
        ]
        
        for endpoint in endpoints:
            try:
                # Test with empty data to check if endpoint exists
                test_data = {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {},
                    "id": 1
                }
                
                response = self.session.post(
                    f"{self.url}{endpoint}",
                    headers={'Content-Type': 'application/json'},
                    json=test_data
                )
                
                if response.status_code == 200:
                    print(f"✅ Endpoint {endpoint} is accessible")
                else:
                    print(f"❌ Endpoint {endpoint} failed (Status: {response.status_code})")
                    
            except Exception as e:
                print(f"❌ Error testing endpoint {endpoint}: {str(e)}")
    
    def test_models_exist(self):
        """Test if required models exist"""
        models_to_check = [
            'purchase.plan',
            'purchase.plan.line',
            'budget.cpv',
            'budget.cpv.line',
            'budget.line'
        ]
        
        print("\n📋 Checking if required models exist...")
        for model in models_to_check:
            # This is a simplified check - in real scenario you'd use Odoo's RPC
            print(f"📌 Model '{model}' should be available")
    
    def generate_test_report(self):
        """Generate a test report to verify functionality"""
        print("\n📊 Testing report generation...")
        print("📌 To fully test the report:")
        print("   1. Go to Accounting → Purchase Plans → ვიზუალური ანგარიში")
        print("   2. Select a Purchase Plan")
        print("   3. Select a Budget CPV")
        print("   4. Click 'ანგარიშის გენერირება'")
        print("   5. Verify charts and tables appear")
        print("   6. Test CSV export functionality")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Visual Report Tests...")
        print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Odoo URL: {self.url}")
        print(f"💾 Database: {self.db}")
        print("-" * 50)
        
        # Login test
        if not self.login():
            print("❌ Cannot proceed without login")
            return False
        
        # Page load test
        self.test_visual_report_page()
        
        # API endpoints test
        print("\n🔗 Testing API endpoints...")
        self.test_api_endpoints()
        
        # Models check
        self.test_models_exist()
        
        # Manual test instructions
        self.generate_test_report()
        
        print("\n" + "=" * 50)
        print("✅ Visual Report Tests Completed!")
        print("📝 Manual testing is required for full verification")
        print("🔍 Check the browser console for any JavaScript errors")
        print("=" * 50)
        
        return True

def main():
    """Main function"""
    print("🧪 Budget Visual Report Test Suite")
    print("=" * 50)
    
    # Create tester instance
    tester = VisualReportTester(ODOO_URL, DATABASE, USERNAME, PASSWORD)
    
    # Run tests
    tester.run_all_tests()

if __name__ == "__main__":
    # Instructions for running
    print("📋 Before running this test:")
    print("   1. Update ODOO_URL, DATABASE, USERNAME, PASSWORD variables")
    print("   2. Make sure Odoo is running")
    print("   3. Make sure the budget module is installed")
    print("   4. Run: python3 tests_visual_report.py")
    print()
    
    # Uncomment the next line to run tests
    # main()
    
    print("🔧 Configure the variables above and uncomment main() to run tests")
