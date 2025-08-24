#!/usr/bin/env python3
"""
Test Runner Script for n8n Workflow Agent System

This script:
1. Checks if required services are running
2. Runs unit tests and integration tests
3. Provides helpful feedback about test results
"""

import asyncio
import httpx
import logging
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestRunner:
    """Manages test execution and service dependencies"""
    
    def __init__(self):
        self.services = {
            "template_service": "http://localhost:8000",
            "n8n": "http://localhost:5678", 
            "agent_api": "http://localhost:3001"
        }
        self.test_files = [
            "test_unit.py",
            "test_integration.py", 
            "test_fastapi_endpoints.py",
            "test_mocks.py",
            "test_error_scenarios.py",
            "test_complete_integration.py"
        ]
    
    async def check_service_health(self, service_name: str, url: str) -> Tuple[bool, Optional[str]]:
        """Check if a service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                if service_name == "template_service":
                    response = await client.get(f"{url}/health")
                elif service_name == "n8n":
                    response = await client.get(f"{url}/rest/workflows")  # Try n8n API
                elif service_name == "agent_api":
                    response = await client.get(f"{url}/health")
                else:
                    response = await client.get(url)
                
                if response.status_code in [200, 401, 403]:  # 401/403 means service exists
                    return True, None
                else:
                    return False, f"HTTP {response.status_code}"
                    
        except httpx.ConnectError:
            return False, "Connection refused"
        except httpx.TimeoutException:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)
    
    async def check_all_services(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        """Check health of all required services"""
        logger.info("🔍 Checking service health...")
        results = {}
        
        for service_name, url in self.services.items():
            is_healthy, error = await self.check_service_health(service_name, url)
            results[service_name] = (is_healthy, error)
            
            if is_healthy:
                logger.info(f"✅ {service_name}: Healthy")
            else:
                logger.warning(f"⚠️  {service_name}: {error}")
        
        return results
    
    def run_pytest(self, test_file: str, markers: List[str] = None, verbose: bool = True) -> bool:
        """Run pytest for a specific test file"""
        cmd = ["python", "-m", "pytest", test_file]
        
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        if verbose:
            cmd.extend(["-v", "--tb=short"])
        
        logger.info(f"🧪 Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ {test_file}: All tests passed")
                if result.stdout:
                    print(result.stdout)
                return True
            else:
                logger.error(f"❌ {test_file}: Tests failed")
                if result.stdout:
                    print("STDOUT:", result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to run {test_file}: {e}")
            return False
    
    def run_unit_tests(self) -> bool:
        """Run unit tests only"""
        logger.info("🧪 Running Unit Tests...")
        return self.run_pytest("test_unit.py", markers=["unit"])
    
    def run_integration_tests(self, service_status: Dict[str, Tuple[bool, Optional[str]]]) -> bool:
        """Run integration tests based on service availability"""
        logger.info("🧪 Running Integration Tests...")
        
        # Determine which integration tests can run based on service availability
        available_markers = []
        
        if service_status["template_service"][0]:
            available_markers.append("template_service")
        
        if service_status["n8n"][0]:
            available_markers.append("n8n")
        
        # Always try to run basic integration tests even if external services aren't available
        # (they should use mocks)
        if not available_markers:
            logger.info("ℹ️  Running integration tests with mocked services only")
            return self.run_pytest("test_integration.py", markers=["integration"])
        else:
            logger.info(f"ℹ️  Running integration tests with markers: {available_markers}")
            return self.run_pytest("test_integration.py", markers=["integration"])
    
    def run_fastapi_tests(self) -> bool:
        """Run FastAPI endpoint tests"""
        logger.info("🌐 Running FastAPI Endpoint Tests...")
        return self.run_pytest("test_fastapi_endpoints.py", markers=["fastapi"])
    
    def run_mock_tests(self) -> bool:
        """Run mocking tests"""
        logger.info("🎭 Running Mock Tests...")
        return self.run_pytest("test_mocks.py", markers=["mocks"])
    
    def run_error_tests(self) -> bool:
        """Run error scenario tests"""
        logger.info("❌ Running Error Scenario Tests...")
        return self.run_pytest("test_error_scenarios.py", markers=["errors"])
    
    def run_complete_tests(self) -> bool:
        """Run complete integration tests"""
        logger.info("🔄 Running Complete Integration Tests...")
        return self.run_pytest("test_complete_integration.py", markers=["complete"])
    
    def print_service_instructions(self, service_status: Dict[str, Tuple[bool, Optional[str]]]):
        """Print instructions for starting missing services"""
        unhealthy_services = [
            service for service, (healthy, _) in service_status.items() 
            if not healthy
        ]
        
        if not unhealthy_services:
            return
        
        logger.info("📋 Instructions for starting missing services:")
        
        for service in unhealthy_services:
            if service == "template_service":
                logger.info("  📦 Template Service:")
                logger.info("     cd /Users/cgordon/workstation/n8n-lab")
                logger.info("     python utils/api_server.py")
                logger.info("")
                
            elif service == "n8n":
                logger.info("  🔧 n8n Service:")
                logger.info("     docker-compose up n8n")
                logger.info("     OR")
                logger.info("     cd /path/to/n8n && npm start")
                logger.info("")
                
            elif service == "agent_api":
                logger.info("  🤖 Agent API:")
                logger.info("     cd /Users/cgordon/workstation/n8n-lab/agent-api")
                logger.info("     python main.py")
                logger.info("")
    
    async def run_all_tests(self):
        """Run complete test suite"""
        logger.info("🚀 Starting n8n Workflow Agent Test Suite")
        logger.info("=" * 50)
        
        # Check service health
        service_status = await self.check_all_services()
        logger.info("")
        
        # Print service instructions if needed
        self.print_service_instructions(service_status)
        
        # Run all test suites
        logger.info("📋 Test Execution Plan:")
        logger.info("  1. Unit Tests (no external dependencies)")
        logger.info("  2. FastAPI Endpoint Tests (with mocking)")
        logger.info("  3. Mock Tests (testing mock functionality)")
        logger.info("  4. Error Scenario Tests (error handling)")
        logger.info("  5. Integration Tests (with service mocking)")
        logger.info("  6. Complete Integration Tests (end-to-end)")
        logger.info("")
        
        # Execute all test suites
        test_results = {}
        
        test_results["unit"] = self.run_unit_tests()
        logger.info("")
        
        test_results["fastapi"] = self.run_fastapi_tests()
        logger.info("")
        
        test_results["mocks"] = self.run_mock_tests()
        logger.info("")
        
        test_results["errors"] = self.run_error_tests()
        logger.info("")
        
        test_results["integration"] = self.run_integration_tests(service_status)
        logger.info("")
        
        test_results["complete"] = self.run_complete_tests()
        logger.info("")
        
        # Summary
        logger.info("📊 Test Results Summary:")
        logger.info("=" * 40)
        logger.info(f"Unit Tests:              {'✅ PASSED' if test_results['unit'] else '❌ FAILED'}")
        logger.info(f"FastAPI Endpoint Tests:  {'✅ PASSED' if test_results['fastapi'] else '❌ FAILED'}")
        logger.info(f"Mock Tests:              {'✅ PASSED' if test_results['mocks'] else '❌ FAILED'}")
        logger.info(f"Error Scenario Tests:    {'✅ PASSED' if test_results['errors'] else '❌ FAILED'}")
        logger.info(f"Integration Tests:       {'✅ PASSED' if test_results['integration'] else '❌ FAILED'}")
        logger.info(f"Complete Integration:    {'✅ PASSED' if test_results['complete'] else '❌ FAILED'}")
        logger.info("")
        
        all_passed = all(test_results.values())
        if all_passed:
            logger.info("🎉 All test suites passed!")
            return True
        else:
            failed_suites = [name for name, passed in test_results.items() if not passed]
            logger.error(f"💥 Failed test suites: {', '.join(failed_suites)}")
            logger.error("Check output above for details.")
            return False


async def main():
    """Main test runner entry point"""
    runner = TestRunner()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg == "unit":
            logger.info("Running unit tests only...")
            success = runner.run_unit_tests()
            sys.exit(0 if success else 1)
            
        elif arg == "integration":
            logger.info("Running integration tests only...")
            service_status = await runner.check_all_services()
            success = runner.run_integration_tests(service_status)
            sys.exit(0 if success else 1)
            
        elif arg == "fastapi":
            logger.info("Running FastAPI endpoint tests only...")
            success = runner.run_fastapi_tests()
            sys.exit(0 if success else 1)
            
        elif arg == "mocks":
            logger.info("Running mock tests only...")
            success = runner.run_mock_tests()
            sys.exit(0 if success else 1)
            
        elif arg == "errors":
            logger.info("Running error scenario tests only...")
            success = runner.run_error_tests()
            sys.exit(0 if success else 1)
            
        elif arg == "complete":
            logger.info("Running complete integration tests only...")
            success = runner.run_complete_tests()
            sys.exit(0 if success else 1)
            
        elif arg == "check":
            logger.info("Checking service health only...")
            await runner.check_all_services()
            sys.exit(0)
        
        elif arg in ["help", "-h", "--help"]:
            print("Usage: python run_tests.py [unit|integration|fastapi|mocks|errors|complete|check|help]")
            print("")
            print("Options:")
            print("  unit         Run unit tests only")
            print("  integration  Run integration tests only")
            print("  fastapi      Run FastAPI endpoint tests only")
            print("  mocks        Run mock tests only")
            print("  errors       Run error scenario tests only")
            print("  complete     Run complete integration tests only")
            print("  check        Check service health only")
            print("  help         Show this help message")
            print("  (no args)    Run all tests")
            sys.exit(0)
    
    # Run all tests
    success = await runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())