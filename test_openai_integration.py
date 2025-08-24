#!/usr/bin/env python3
"""
Test script to verify Open WebUI integration with n8n Agent API

This script tests the OpenAI-compatible endpoints that were added for Open WebUI integration.
"""

import asyncio
import httpx
import sys


class OpenAIIntegrationTester:
    """Test class for OpenAI-compatible endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def test_health_endpoint(self) -> bool:
        """Test the health endpoint"""
        print("🔍 Testing health endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health check passed: {health_data.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {str(e)}")
            return False
    
    async def test_models_endpoint(self) -> bool:
        """Test the /v1/models endpoint"""
        print("🔍 Testing /v1/models endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/v1/models")
            if response.status_code == 200:
                models_data = response.json()
                models = models_data.get('data', [])
                print(f"✅ Models endpoint passed: {len(models)} model(s) available")
                for model in models:
                    print(f"   - {model.get('id', 'unknown')}")
                return True
            else:
                print(f"❌ Models endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Models endpoint error: {str(e)}")
            return False
    
    async def test_chat_completions_endpoint(self) -> bool:
        """Test the /v1/chat/completions endpoint"""
        print("🔍 Testing /v1/chat/completions endpoint...")
        
        test_request = {
            "model": "n8n-workflow-assistant",
            "messages": [
                {"role": "user", "content": "Hello, can you help me create a simple workflow?"}
            ],
            "temperature": 0.7
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json=test_request
            )
            
            if response.status_code == 200:
                chat_data = response.json()
                choices = chat_data.get('choices', [])
                if choices and len(choices) > 0:
                    message = choices[0].get('message', {}).get('content', '')
                    print(f"✅ Chat completions endpoint passed")
                    print(f"   Response length: {len(message)} characters")
                    print(f"   Usage: {chat_data.get('usage', {})}")
                    return True
                else:
                    print("❌ Chat completions endpoint returned empty response")
                    return False
            else:
                print(f"❌ Chat completions endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Chat completions endpoint error: {str(e)}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all integration tests"""
        print("🚀 Starting Open WebUI Integration Tests")
        print("=" * 50)
        
        tests = [
            ("Health Endpoint", self.test_health_endpoint),
            ("Models Endpoint", self.test_models_endpoint),
            ("Chat Completions Endpoint", self.test_chat_completions_endpoint),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n📋 Running {test_name}...")
            result = await test_func()
            results.append((test_name, result))
        
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        
        all_passed = True
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status} - {test_name}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 50)
        if all_passed:
            print("🎉 All tests passed! Open WebUI integration is ready.")
        else:
            print("⚠️  Some tests failed. Please check the agent-api service.")
        
        return all_passed


async def main():
    """Main test runner"""
    # Check if a custom URL was provided
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
    
    print(f"🔧 Testing Open WebUI integration at: {base_url}")
    
    tester = OpenAIIntegrationTester(base_url)
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())