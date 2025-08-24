#!/usr/bin/env python3
"""
Comprehensive LLM Understanding Test Suite for n8n Workflow Intent Extraction

This script tests the OpenRouter LLM's ability to understand and extract
workflow intents from natural language requests of varying complexity.
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import os
import sys
from pathlib import Path

# Add the agent-api directory to path for imports
sys.path.append(str(Path(__file__).parent / "agent-api"))

from llm_client import LLMClient

@dataclass
class TestCase:
    """Test case structure for workflow requests"""
    category: str
    description: str
    request: str
    expected_integrations: List[str]
    expected_trigger_type: str
    expected_action_keywords: List[str]
    complexity_level: str  # "simple", "moderate", "complex", "ambiguous", "edge_case"

@dataclass
class TestResult:
    """Test result structure"""
    test_case: TestCase
    extracted_intent: Dict[str, Any]
    response_time_ms: float
    accuracy_scores: Dict[str, float]
    passed: bool
    errors: List[str]

class IntentExtractionTester:
    """Main test class for validating LLM intent extraction"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.test_cases = self._create_test_cases()
        self.results: List[TestResult] = []
    
    def _create_test_cases(self) -> List[TestCase]:
        """Create comprehensive test cases covering various scenarios"""
        test_cases = []
        
        # === SIMPLE REQUESTS ===
        test_cases.extend([
            TestCase(
                category="Simple",
                description="Basic webhook to Slack",
                request="Create a webhook that posts to Slack",
                expected_integrations=["Webhook", "Slack"],
                expected_trigger_type="webhook",
                expected_action_keywords=["post", "message", "notification"],
                complexity_level="simple"
            ),
            TestCase(
                category="Simple",
                description="Email notifications for forms",
                request="Send email notifications for form submissions",
                expected_integrations=["Email", "Form"],
                expected_trigger_type="webhook",
                expected_action_keywords=["send", "email", "notification", "form"],
                complexity_level="simple"
            ),
            TestCase(
                category="Simple",
                description="Scheduled reports",
                request="Schedule daily reports to Google Sheets",
                expected_integrations=["Google Sheets", "Schedule"],
                expected_trigger_type="schedule",
                expected_action_keywords=["daily", "report", "schedule"],
                complexity_level="simple"
            )
        ])
        
        # === MODERATE COMPLEXITY ===
        test_cases.extend([
            TestCase(
                category="Moderate",
                description="GitHub to email automation",
                request="Set up automated email notifications when GitHub issues are created",
                expected_integrations=["GitHub", "Email"],
                expected_trigger_type="webhook",
                expected_action_keywords=["automated", "notification", "issues", "created"],
                complexity_level="moderate"
            ),
            TestCase(
                category="Moderate",
                description="Form processing with validation",
                request="Process form submissions, validate email addresses, and add to CRM",
                expected_integrations=["Form", "Email Validation", "CRM"],
                expected_trigger_type="webhook",
                expected_action_keywords=["process", "validate", "email", "crm"],
                complexity_level="moderate"
            ),
            TestCase(
                category="Moderate",
                description="Website monitoring with Discord",
                request="Monitor website changes and notify team via Discord",
                expected_integrations=["Website Monitor", "Discord"],
                expected_trigger_type="schedule",
                expected_action_keywords=["monitor", "changes", "notify", "team"],
                complexity_level="moderate"
            )
        ])
        
        # === COMPLEX MULTI-STEP ===
        test_cases.extend([
            TestCase(
                category="Complex",
                description="Multi-step form processing workflow",
                request="Build a workflow that processes form submissions, validates data, stores in Airtable, and sends Slack notifications with approval workflow",
                expected_integrations=["Form", "Data Validation", "Airtable", "Slack"],
                expected_trigger_type="webhook",
                expected_action_keywords=["process", "validate", "store", "notification", "approval"],
                complexity_level="complex"
            ),
            TestCase(
                category="Complex",
                description="E-commerce order processing",
                request="Create an e-commerce order processing system that updates inventory, sends confirmation emails, and creates shipping labels",
                expected_integrations=["E-commerce", "Inventory", "Email", "Shipping"],
                expected_trigger_type="webhook",
                expected_action_keywords=["order", "inventory", "confirmation", "shipping", "labels"],
                complexity_level="complex"
            ),
            TestCase(
                category="Complex",
                description="Customer support automation",
                request="Automate customer support tickets: receive via email, categorize using AI, assign to team members, and track resolution in database",
                expected_integrations=["Email", "AI", "Database", "Team Assignment"],
                expected_trigger_type="triggered",
                expected_action_keywords=["support", "categorize", "assign", "track", "resolution"],
                complexity_level="complex"
            )
        ])
        
        # === AMBIGUOUS/CHALLENGING ===
        test_cases.extend([
            TestCase(
                category="Ambiguous",
                description="Vague marketing automation",
                request="Help me automate my marketing tasks",
                expected_integrations=[],  # Should be empty or generic
                expected_trigger_type="manual",
                expected_action_keywords=["automate", "marketing", "tasks"],
                complexity_level="ambiguous"
            ),
            TestCase(
                category="Ambiguous",
                description="Vague data flow improvement",
                request="Make my data flow better",
                expected_integrations=[],
                expected_trigger_type="manual",
                expected_action_keywords=["data", "flow", "improve"],
                complexity_level="ambiguous"
            ),
            TestCase(
                category="Ambiguous",
                description="Generic notifications",
                request="Set up some notifications",
                expected_integrations=["Notification"],
                expected_trigger_type="manual",
                expected_action_keywords=["notification", "setup"],
                complexity_level="ambiguous"
            )
        ])
        
        # === EDGE CASES ===
        test_cases.extend([
            TestCase(
                category="Edge Case",
                description="Very short request",
                request="Slack bot",
                expected_integrations=["Slack"],
                expected_trigger_type="manual",
                expected_action_keywords=["bot", "slack"],
                complexity_level="edge_case"
            ),
            TestCase(
                category="Edge Case",
                description="Request with typos",
                request="Creat a webhok that post to slak when somone submits form",
                expected_integrations=["Webhook", "Slack", "Form"],
                expected_trigger_type="webhook",
                expected_action_keywords=["create", "webhook", "post", "slack", "form"],
                complexity_level="edge_case"
            ),
            TestCase(
                category="Edge Case",
                description="Mixed terminology",
                request="Build automation for email → sheets workflow with triggers",
                expected_integrations=["Email", "Sheets"],
                expected_trigger_type="triggered",
                expected_action_keywords=["automation", "email", "sheets", "workflow"],
                complexity_level="edge_case"
            ),
            TestCase(
                category="Edge Case",
                description="Very long detailed request",
                request="""I need to create a comprehensive workflow automation system that handles multiple business processes: 
                First, when customers submit contact forms on our website, the system should automatically validate their email addresses 
                and phone numbers, then store the validated information in our CRM system. If validation fails, it should send an 
                automated response asking for correct information. For successful submissions, create a lead record in Salesforce, 
                send a welcome email series, and notify our sales team via Slack with prospect details. Additionally, the system 
                should track engagement metrics, schedule follow-up reminders, and integrate with our marketing automation platform 
                to add prospects to appropriate email campaigns based on their submitted interests. The workflow should also handle 
                error cases gracefully and provide detailed logging for troubleshooting purposes.""",
                expected_integrations=["Form", "Email Validation", "CRM", "Salesforce", "Email", "Slack", "Marketing Automation"],
                expected_trigger_type="webhook",
                expected_action_keywords=["validate", "store", "crm", "email", "slack", "notify", "tracking", "follow-up"],
                complexity_level="edge_case"
            ),
            TestCase(
                category="Edge Case",
                description="Mixed language/special characters",
                request="Create webhook für Slack notifications (émails → Discord) with ⚡ speed",
                expected_integrations=["Webhook", "Slack", "Email", "Discord"],
                expected_trigger_type="webhook",
                expected_action_keywords=["webhook", "slack", "notifications", "discord"],
                complexity_level="edge_case"
            )
        ])
        
        return test_cases
    
    async def run_single_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case and return results"""
        print(f"\n🧪 Testing: {test_case.description}")
        print(f"   Request: {test_case.request[:100]}{'...' if len(test_case.request) > 100 else ''}")
        
        errors = []
        
        try:
            # Measure response time
            start_time = time.time()
            extracted_intent = await self.llm_client.openrouter.extract_intent(test_case.request)
            response_time_ms = (time.time() - start_time) * 1000
            
            print(f"   ⏱️  Response time: {response_time_ms:.1f}ms")
            print(f"   📊 Extracted: {json.dumps(extracted_intent, indent=2)}")
            
            # Calculate accuracy scores
            accuracy_scores = self._calculate_accuracy_scores(test_case, extracted_intent)
            
            # Determine if test passed
            passed = self._evaluate_test_result(test_case, extracted_intent, accuracy_scores)
            
        except Exception as e:
            errors.append(f"Execution error: {str(e)}")
            extracted_intent = {}
            response_time_ms = 0.0
            accuracy_scores = {"overall": 0.0}
            passed = False
            print(f"   ❌ Error: {str(e)}")
        
        return TestResult(
            test_case=test_case,
            extracted_intent=extracted_intent,
            response_time_ms=response_time_ms,
            accuracy_scores=accuracy_scores,
            passed=passed,
            errors=errors
        )
    
    def _calculate_accuracy_scores(self, test_case: TestCase, extracted: Dict[str, Any]) -> Dict[str, float]:
        """Calculate accuracy scores for different aspects of the extraction"""
        scores = {}
        
        # Integration detection accuracy
        extracted_integrations = [i.lower() for i in extracted.get("integrations", [])]
        expected_integrations = [i.lower() for i in test_case.expected_integrations]
        
        if expected_integrations:
            correct_integrations = sum(1 for exp in expected_integrations 
                                     if any(exp in ext or ext in exp for ext in extracted_integrations))
            precision = correct_integrations / len(extracted_integrations) if extracted_integrations else 0
            recall = correct_integrations / len(expected_integrations) if expected_integrations else 0
            scores["integration_precision"] = precision * 100
            scores["integration_recall"] = recall * 100
            scores["integration_f1"] = (2 * precision * recall / (precision + recall) * 100) if (precision + recall) > 0 else 0
        else:
            scores["integration_precision"] = 100.0 if not extracted_integrations else 50.0
            scores["integration_recall"] = 100.0
            scores["integration_f1"] = scores["integration_precision"]
        
        # Trigger type accuracy
        extracted_trigger = extracted.get("trigger_type", "").lower()
        expected_trigger = test_case.expected_trigger_type.lower()
        scores["trigger_accuracy"] = 100.0 if extracted_trigger == expected_trigger else 0.0
        
        # Action keywords presence
        action_text = extracted.get("action", "").lower()
        keyword_hits = sum(1 for keyword in test_case.expected_action_keywords 
                          if keyword.lower() in action_text)
        scores["action_keyword_coverage"] = (keyword_hits / len(test_case.expected_action_keywords) * 100) if test_case.expected_action_keywords else 100.0
        
        # JSON structure completeness
        required_fields = ["integrations", "trigger_type", "action", "requirements"]
        present_fields = sum(1 for field in required_fields if field in extracted)
        scores["structure_completeness"] = (present_fields / len(required_fields)) * 100
        
        # Overall score (weighted average)
        weights = {
            "integration_f1": 0.3,
            "trigger_accuracy": 0.25,
            "action_keyword_coverage": 0.25,
            "structure_completeness": 0.2
        }
        scores["overall"] = sum(scores[key] * weight for key, weight in weights.items())
        
        return scores
    
    def _evaluate_test_result(self, test_case: TestCase, extracted: Dict[str, Any], scores: Dict[str, float]) -> bool:
        """Evaluate if a test result is acceptable based on complexity and expectations"""
        overall_score = scores.get("overall", 0)
        
        # Different thresholds based on complexity
        thresholds = {
            "simple": 80.0,      # High expectations for simple cases
            "moderate": 70.0,    # Good performance expected
            "complex": 60.0,     # Lower threshold due to complexity
            "ambiguous": 40.0,   # Very low threshold - these are intentionally vague
            "edge_case": 50.0    # Medium threshold - edge cases are tricky
        }
        
        threshold = thresholds.get(test_case.complexity_level, 70.0)
        
        # Additional validation: must have basic structure
        has_structure = all(field in extracted for field in ["integrations", "trigger_type", "action"])
        
        return overall_score >= threshold and has_structure
    
    async def run_all_tests(self) -> None:
        """Run all test cases and collect results"""
        print("🚀 Starting LLM Intent Extraction Test Suite")
        print("=" * 60)
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n[{i}/{len(self.test_cases)}] Category: {test_case.category}")
            result = await self.run_single_test(test_case)
            self.results.append(result)
            
            # Show immediate result
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"   {status} (Overall: {result.accuracy_scores.get('overall', 0):.1f}%)")
            
            # Small delay to be respectful to the API
            await asyncio.sleep(0.5)
    
    def generate_report(self) -> None:
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        # Overall statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        overall_pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\nOverall Results:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {total_tests - passed_tests}")
        print(f"  Pass Rate: {overall_pass_rate:.1f}%")
        
        # Performance metrics
        response_times = [r.response_time_ms for r in self.results if r.response_time_ms > 0]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            print(f"\nPerformance Metrics:")
            print(f"  Average Response Time: {avg_response_time:.1f}ms")
            print(f"  Fastest Response: {min_response_time:.1f}ms")
            print(f"  Slowest Response: {max_response_time:.1f}ms")
        
        # Category breakdown
        categories = {}
        for result in self.results:
            cat = result.test_case.category
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0, "scores": []}
            categories[cat]["total"] += 1
            if result.passed:
                categories[cat]["passed"] += 1
            categories[cat]["scores"].append(result.accuracy_scores.get("overall", 0))
        
        print(f"\nResults by Category:")
        for cat, stats in categories.items():
            pass_rate = (stats["passed"] / stats["total"]) * 100
            avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
            print(f"  {cat:12} | Pass: {stats['passed']:2}/{stats['total']:2} ({pass_rate:5.1f}%) | Avg Score: {avg_score:5.1f}%")
        
        # Detailed accuracy metrics
        all_scores = {}
        metric_names = ["integration_f1", "trigger_accuracy", "action_keyword_coverage", "structure_completeness", "overall"]
        
        for metric in metric_names:
            scores = [r.accuracy_scores.get(metric, 0) for r in self.results]
            if scores:
                all_scores[metric] = {
                    "avg": sum(scores) / len(scores),
                    "min": min(scores),
                    "max": max(scores)
                }
        
        print(f"\nAccuracy Metrics (Average):")
        for metric, stats in all_scores.items():
            metric_display = metric.replace("_", " ").title()
            print(f"  {metric_display:25} | Avg: {stats['avg']:5.1f}% | Range: {stats['min']:5.1f}%-{stats['max']:5.1f}%")
        
        # Failed test analysis
        failed_tests = [r for r in self.results if not r.passed]
        if failed_tests:
            print(f"\n❌ Failed Tests Analysis:")
            for i, result in enumerate(failed_tests, 1):
                print(f"\n  {i}. {result.test_case.description}")
                print(f"     Request: {result.test_case.request[:100]}{'...' if len(result.test_case.request) > 100 else ''}")
                print(f"     Overall Score: {result.accuracy_scores.get('overall', 0):.1f}%")
                print(f"     Issues: {', '.join(result.errors) if result.errors else 'Low accuracy score'}")
                
                # Show what was expected vs extracted
                print(f"     Expected Integrations: {result.test_case.expected_integrations}")
                print(f"     Extracted Integrations: {result.extracted_intent.get('integrations', [])}")
                print(f"     Expected Trigger: {result.test_case.expected_trigger_type}")
                print(f"     Extracted Trigger: {result.extracted_intent.get('trigger_type', 'N/A')}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if overall_pass_rate >= 80:
            print("  ✅ Excellent performance! The LLM shows strong n8n workflow understanding.")
        elif overall_pass_rate >= 60:
            print("  ⚠️  Good performance with room for improvement. Focus on complex scenarios.")
        else:
            print("  ❌ Performance needs improvement. Consider prompt engineering or model fine-tuning.")
        
        # Specific recommendations based on failed categories
        for cat, stats in categories.items():
            pass_rate = (stats["passed"] / stats["total"]) * 100
            if pass_rate < 70:
                if cat == "Ambiguous":
                    print(f"  📝 {cat} requests need better handling - consider clarification prompts.")
                elif cat == "Edge Case":
                    print(f"  🔧 {cat} handling needs improvement - enhance error correction and normalization.")
                elif cat == "Complex":
                    print(f"  🧠 {cat} scenarios need better parsing - consider multi-step intent extraction.")
                else:
                    print(f"  ⚙️  {cat} category needs attention - review expectations and prompts.")
        
        print("\n" + "=" * 60)

async def main():
    """Main test execution function"""
    # Verify API key is available
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY environment variable not found")
        print("Please set your OpenRouter API key in the .env file")
        return 1
    
    print("🔑 OpenRouter API key found")
    print(f"🔗 API key preview: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        tester = IntentExtractionTester()
        await tester.run_all_tests()
        tester.generate_report()
        
        # Return appropriate exit code
        total_tests = len(tester.results)
        passed_tests = sum(1 for r in tester.results if r.passed)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        return 0 if pass_rate >= 70 else 1  # Return error code if pass rate is below 70%
        
    except Exception as e:
        print(f"❌ Test suite execution failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)