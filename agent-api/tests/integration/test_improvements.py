"""
Enhanced Testing Framework for LLM Intent Extraction Improvements
Provides A/B testing capabilities to compare original vs improved extraction
"""

import asyncio
import json
import time
import statistics
from typing import Dict, Any, List, Tuple
import sys
import os

# Add the parent directory to sys.path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_client import OpenRouterClient


class ExtractionTester:
    """Test framework for comparing intent extraction methods"""
    
    def __init__(self):
        # Initialize both clients
        self.enhanced_client = OpenRouterClient()
        
        # Test cases from the original comprehensive testing
        self.test_cases = [
            # Simple category (previously 33.3% pass rate - critical)
            {
                "request": "Create a webhook that posts to Slack when triggered",
                "expected": {
                    "integrations": ["Webhook", "Slack"],
                    "trigger_type": "webhook"
                },
                "category": "simple",
                "difficulty": "high_priority"  # Failed in original testing
            },
            {
                "request": "Send email notifications when form is submitted", 
                "expected": {
                    "integrations": ["Email", "Form"],
                    "trigger_type": "webhook"
                },
                "category": "simple",
                "difficulty": "high_priority"  # Failed in original testing
            },
            {
                "request": "Schedule daily reports to Google Sheets",
                "expected": {
                    "integrations": ["Schedule", "Sheets"],
                    "trigger_type": "schedule"
                },
                "category": "simple",
                "difficulty": "medium"
            },
            
            # Moderate category (previously 33.3% pass rate)
            {
                "request": "Process form submissions and update CRM database",
                "expected": {
                    "integrations": ["Form", "Database"],
                    "trigger_type": "webhook"
                },
                "category": "moderate", 
                "difficulty": "high"
            },
            {
                "request": "Email notifications for form submissions with data validation",
                "expected": {
                    "integrations": ["Email", "Form"],
                    "trigger_type": "webhook"
                },
                "category": "moderate",
                "difficulty": "high"
            },
            {
                "request": "Automatically backup database to cloud storage daily",
                "expected": {
                    "integrations": ["Database", "Storage", "Schedule"],
                    "trigger_type": "schedule"
                },
                "category": "moderate",
                "difficulty": "medium"
            },
            
            # Complex category (previously 66.7% pass rate - good baseline)
            {
                "request": "Build workflow for customer support ticket routing with Slack notifications and database logging",
                "expected": {
                    "integrations": ["Database", "Slack"],
                    "trigger_type": "webhook"
                },
                "category": "complex",
                "difficulty": "medium"
            },
            
            # Edge cases for robustness testing
            {
                "request": "webhook for slack notifications",  # Minimal case
                "expected": {
                    "integrations": ["Webhook", "Slack"],
                    "trigger_type": "webhook"
                },
                "category": "edge_case",
                "difficulty": "high"
            },
            {
                "request": "Form data to airtable when submitted",  # Implicit webhook
                "expected": {
                    "integrations": ["Form", "Airtable"], 
                    "trigger_type": "webhook"
                },
                "category": "edge_case",
                "difficulty": "high"
            }
        ]
    
    async def test_enhanced_extraction(self) -> Dict[str, Any]:
        """Test the enhanced extraction method on all test cases"""
        print("🧪 Testing Enhanced Intent Extraction")
        print("=" * 60)
        
        results = {
            "test_results": [],
            "category_performance": {},
            "overall_metrics": {}
        }
        
        total_tests = 0
        passed_tests = 0
        total_response_time = 0
        
        # Track performance by category
        category_stats = {}
        
        for i, test_case in enumerate(self.test_cases):
            print(f"\nTest {i+1}/{len(self.test_cases)}: {test_case['category'].upper()}")
            print(f"Request: {test_case['request']}")
            print(f"Expected: {test_case['expected']}")
            
            start_time = time.time()
            
            try:
                # Use enhanced extraction method
                intent, confidence, corrections = await self.enhanced_client.extract_intent_with_validation(
                    test_case['request']
                )
                
                response_time = (time.time() - start_time) * 1000
                total_response_time += response_time
                
                # Evaluate the result
                passed, score, analysis = self._evaluate_result(intent, test_case['expected'])
                
                result = {
                    "test_case": test_case,
                    "extracted_intent": intent,
                    "confidence_score": confidence,
                    "corrections_applied": corrections,
                    "passed": passed,
                    "score": score,
                    "response_time_ms": response_time,
                    "analysis": analysis
                }
                
                results["test_results"].append(result)
                
                # Update category stats
                category = test_case['category']
                if category not in category_stats:
                    category_stats[category] = {"passed": 0, "total": 0, "scores": []}
                
                category_stats[category]["total"] += 1
                category_stats[category]["scores"].append(score)
                if passed:
                    category_stats[category]["passed"] += 1
                    passed_tests += 1
                
                total_tests += 1
                
                # Display result
                status = "✅ PASSED" if passed else "❌ FAILED"
                print(f"Result: {status} (Score: {score:.1f}%, Confidence: {confidence:.2f})")
                print(f"Response Time: {response_time:.0f}ms")
                if corrections:
                    print(f"Corrections: {corrections}")
                if analysis:
                    print(f"Analysis: {analysis}")
                
            except Exception as e:
                print(f"❌ ERROR: {str(e)}")
                result = {
                    "test_case": test_case,
                    "error": str(e),
                    "passed": False,
                    "score": 0
                }
                results["test_results"].append(result)
                total_tests += 1
        
        # Calculate overall metrics
        overall_pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        avg_response_time = total_response_time / total_tests if total_tests > 0 else 0
        
        results["overall_metrics"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "pass_rate": overall_pass_rate,
            "avg_response_time_ms": avg_response_time
        }
        
        # Calculate category performance
        for category, stats in category_stats.items():
            pass_rate = (stats["passed"] / stats["total"]) * 100
            avg_score = statistics.mean(stats["scores"]) if stats["scores"] else 0
            
            results["category_performance"][category] = {
                "pass_rate": pass_rate,
                "avg_score": avg_score,
                "passed": stats["passed"],
                "total": stats["total"]
            }
        
        return results
    
    def _evaluate_result(self, actual: Dict[str, Any], expected: Dict[str, Any]) -> Tuple[bool, float, str]:
        """
        Evaluate extracted intent against expected result
        
        Returns:
            Tuple of (passed, score_percentage, analysis_text)
        """
        score = 0.0
        max_score = 100.0
        issues = []
        
        # Integration evaluation (50 points)
        actual_integrations = set(actual.get('integrations', []))
        expected_integrations = set(expected.get('integrations', []))
        
        if actual_integrations == expected_integrations:
            score += 50
        else:
            # Partial credit for intersection
            intersection = actual_integrations.intersection(expected_integrations)
            union = actual_integrations.union(expected_integrations)
            
            if union:
                integration_score = (len(intersection) / len(union)) * 50
                score += integration_score
            
            missing = expected_integrations - actual_integrations
            extra = actual_integrations - expected_integrations
            
            if missing:
                issues.append(f"Missing integrations: {list(missing)}")
            if extra:
                issues.append(f"Extra integrations: {list(extra)}")
        
        # Trigger type evaluation (30 points)
        actual_trigger = actual.get('trigger_type', '')
        expected_trigger = expected.get('trigger_type', '')
        
        if actual_trigger == expected_trigger:
            score += 30
        else:
            issues.append(f"Wrong trigger: got '{actual_trigger}', expected '{expected_trigger}'")
        
        # Structure completeness (20 points)
        required_fields = ['integrations', 'trigger_type', 'action']
        if all(field in actual and actual[field] for field in required_fields):
            score += 20
        else:
            missing_fields = [field for field in required_fields if not actual.get(field)]
            if missing_fields:
                issues.append(f"Missing/empty fields: {missing_fields}")
        
        # Determine if passed (75% threshold)
        passed = score >= 75.0
        
        analysis = f"Issues: {'; '.join(issues)}" if issues else "Perfect match"
        
        return passed, score, analysis
    
    def print_detailed_report(self, results: Dict[str, Any]):
        """Print comprehensive test results report"""
        print("\n" + "=" * 80)
        print("🎯 ENHANCED INTENT EXTRACTION TEST RESULTS")
        print("=" * 80)
        
        overall = results["overall_metrics"]
        print(f"\n📊 OVERALL PERFORMANCE:")
        print(f"Total Tests: {overall['total_tests']}")
        print(f"Passed: {overall['passed_tests']}")
        print(f"Pass Rate: {overall['pass_rate']:.1f}%")
        print(f"Average Response Time: {overall['avg_response_time_ms']:.0f}ms")
        
        print(f"\n📈 CATEGORY BREAKDOWN:")
        for category, stats in results["category_performance"].items():
            status_emoji = "✅" if stats['pass_rate'] >= 75 else "⚠️" if stats['pass_rate'] >= 60 else "❌"
            print(f"{status_emoji} {category.upper()}: {stats['pass_rate']:.1f}% ({stats['passed']}/{stats['total']}) - Avg Score: {stats['avg_score']:.1f}%")
        
        print(f"\n🔍 DETAILED ANALYSIS:")
        
        high_priority_tests = [r for r in results["test_results"] if r["test_case"].get("difficulty") == "high_priority"]
        if high_priority_tests:
            hp_passed = sum(1 for r in high_priority_tests if r["passed"])
            hp_total = len(high_priority_tests)
            print(f"High Priority Tests (previously failed): {hp_passed}/{hp_total} ({hp_passed/hp_total*100:.1f}%)")
        
        # Show improvements in simple category (critical issue)
        simple_results = results["category_performance"].get("simple", {})
        if simple_results:
            print(f"Simple Category Improvement: {simple_results['pass_rate']:.1f}% (Target: 75%+)")
        
        print(f"\n📋 INDIVIDUAL TEST RESULTS:")
        for i, result in enumerate(results["test_results"]):
            tc = result["test_case"]
            status = "✅" if result["passed"] else "❌"
            
            print(f"{i+1:2}. {status} {tc['category']:<12} | Score: {result.get('score', 0):5.1f}% | " +
                  f"Confidence: {result.get('confidence_score', 0):.2f} | " +
                  f"Time: {result.get('response_time_ms', 0):4.0f}ms")
            
            if not result["passed"] and "analysis" in result:
                print(f"    {result['analysis']}")
            
            if result.get("corrections_applied"):
                print(f"    Corrections: {result['corrections_applied']}")
        
        # Performance comparison with baseline
        print(f"\n🎯 IMPROVEMENT ANALYSIS:")
        simple_rate = results["category_performance"].get("simple", {}).get("pass_rate", 0)
        moderate_rate = results["category_performance"].get("moderate", {}).get("pass_rate", 0)
        
        print(f"Simple Category:   {simple_rate:5.1f}% (was 33.3% - {'✅ Improved' if simple_rate > 33.3 else '❌ No improvement'})")
        print(f"Moderate Category: {moderate_rate:5.1f}% (was 33.3% - {'✅ Improved' if moderate_rate > 33.3 else '❌ No improvement'})")
        print(f"Overall Target:    {overall['pass_rate']:5.1f}% (target: 80%+ - {'✅ Met' if overall['pass_rate'] >= 80 else '⚠️ Needs more work'})")


async def main():
    """Run the enhanced testing framework"""
    tester = ExtractionTester()
    
    print("🚀 Starting Enhanced Intent Extraction Testing...")
    print("Testing improvements to address:")
    print("  - Webhook detection gaps (66.3% → 85%+ target)")
    print("  - Simple request processing (33.3% → 75%+ target)")
    print("  - Trigger type confusion (64.7% → 80%+ target)")
    
    results = await tester.test_enhanced_extraction()
    tester.print_detailed_report(results)
    
    # Save results for analysis
    with open("/Users/cgordon/workstation/n8n-lab/enhanced_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to enhanced_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())