#!/usr/bin/env python3
"""
Standalone test script for enhanced intent extraction
Tests the improvements directly
"""

import asyncio
import json
import time
import os
import sys
from typing import Dict, Any, List, Tuple

# Set up environment - load API key from environment
if "OPENROUTER_API_KEY" not in os.environ:
    print("ERROR: OPENROUTER_API_KEY environment variable not set")
    print("Please set: export OPENROUTER_API_KEY='your-api-key-here'")
    sys.exit(1)

# Add agent-api directory to path
sys.path.insert(0, '/Users/cgordon/workstation/n8n-lab/agent-api')

from llm_client import OpenRouterClient

async def test_enhanced_extraction():
    """Test the enhanced extraction on key problematic cases"""
    
    client = OpenRouterClient()
    
    # Test cases that previously failed (from original comprehensive testing)
    test_cases = [
        {
            "request": "Create a webhook that posts to Slack when triggered",
            "expected": {
                "integrations": ["Webhook", "Slack"],
                "trigger_type": "webhook"
            },
            "category": "simple - previously failed",
            "priority": "critical"
        },
        {
            "request": "Send email notifications when form is submitted",
            "expected": {
                "integrations": ["Email", "Form"], 
                "trigger_type": "webhook"
            },
            "category": "simple - previously failed",
            "priority": "critical"
        },
        {
            "request": "Schedule daily reports to Google Sheets",
            "expected": {
                "integrations": ["Schedule", "Sheets"],
                "trigger_type": "schedule" 
            },
            "category": "simple - baseline",
            "priority": "medium"
        },
        {
            "request": "webhook for slack notifications",  # Minimal case
            "expected": {
                "integrations": ["Webhook", "Slack"],
                "trigger_type": "webhook"
            },
            "category": "edge case",
            "priority": "high"
        },
        {
            "request": "Process form submissions and update CRM database",
            "expected": {
                "integrations": ["Form", "Database"],
                "trigger_type": "webhook"
            },
            "category": "moderate - previously failed",
            "priority": "critical"
        }
    ]
    
    print("🧪 ENHANCED INTENT EXTRACTION VALIDATION TEST")
    print("=" * 70)
    print("Testing improvements to address:")
    print("  ⚠️ Simple request processing (33.3% → 75%+ target)")
    print("  ⚠️ Webhook detection gaps (frequently missed)")  
    print("  ⚠️ Trigger type confusion (defaults to 'manual')")
    print()
    print("KEY IMPROVEMENTS IMPLEMENTED:")
    print("  ✅ Enhanced system prompt with explicit detection rules")
    print("  ✅ Multi-pass validation and correction framework")
    print("  ✅ Optimized temperature (0.3 → 0.1) for consistency")
    print("  ✅ Integration normalization (Gmail→Email, etc.)")
    print()
    
    passed_tests = 0
    total_tests = len(test_cases)
    critical_passed = 0
    critical_total = 0
    total_response_time = 0
    all_corrections = []
    
    for i, test_case in enumerate(test_cases):
        print(f"Test {i+1}/{total_tests}: {test_case['category']}")
        print(f"Request: '{test_case['request']}'")
        print(f"Expected: {test_case['expected']}")
        
        start_time = time.time()
        
        try:
            # Test enhanced extraction method
            intent, confidence, corrections = await client.extract_intent_with_validation(
                test_case['request']
            )
            
            response_time = (time.time() - start_time) * 1000
            total_response_time += response_time
            
            if corrections:
                all_corrections.extend(corrections)
            
            # Evaluate result
            actual_integrations = set(intent.get('integrations', []))
            expected_integrations = set(test_case['expected'].get('integrations', []))
            
            actual_trigger = intent.get('trigger_type', '')
            expected_trigger = test_case['expected'].get('trigger_type', '')
            
            integrations_match = actual_integrations == expected_integrations
            trigger_match = actual_trigger == expected_trigger
            
            passed = integrations_match and trigger_match
            if passed:
                passed_tests += 1
            
            # Track critical test performance
            if test_case['priority'] == 'critical':
                critical_total += 1
                if passed:
                    critical_passed += 1
            
            # Results
            status = "✅ PASSED" if passed else "❌ FAILED"
            priority_icon = "🔥" if test_case['priority'] == 'critical' else "⚡" if test_case['priority'] == 'high' else "📝"
            
            print(f"Result: {status} {priority_icon}")
            print(f"  Extracted: integrations={list(intent.get('integrations', []))}, trigger='{intent.get('trigger_type', '')}'")
            print(f"  Confidence: {confidence:.2f} | Response Time: {response_time:.0f}ms")
            
            if corrections:
                print(f"  🔧 Corrections Applied: {corrections}")
            
            if not passed:
                if not integrations_match:
                    missing = expected_integrations - actual_integrations
                    extra = actual_integrations - expected_integrations
                    if missing:
                        print(f"  ❌ Missing integrations: {list(missing)}")
                    if extra:
                        print(f"  ❌ Extra integrations: {list(extra)}")
                
                if not trigger_match:
                    print(f"  ❌ Wrong trigger: got '{actual_trigger}', expected '{expected_trigger}'")
            
            print()
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            print()
    
    # Calculate metrics
    pass_rate = (passed_tests / total_tests) * 100
    critical_pass_rate = (critical_passed / critical_total) * 100 if critical_total > 0 else 0
    avg_response_time = total_response_time / total_tests
    
    # Summary
    print("=" * 70)
    print("🎯 VALIDATION RESULTS")
    print("=" * 70)
    print(f"Overall Performance: {passed_tests}/{total_tests} ({pass_rate:.1f}%)")
    print(f"Critical Tests (previously failed): {critical_passed}/{critical_total} ({critical_pass_rate:.1f}%)")
    print(f"Average Response Time: {avg_response_time:.0f}ms")
    print(f"Total Corrections Applied: {len(all_corrections)}")
    
    print(f"\n📊 IMPROVEMENT ANALYSIS:")
    print(f"  Baseline Simple Category: 33.3% pass rate")
    print(f"  Current Performance: {pass_rate:.1f}% pass rate")
    improvement = pass_rate - 33.3
    print(f"  Improvement: {improvement:+.1f} percentage points")
    
    print(f"\n🔧 CORRECTION EFFECTIVENESS:")
    if all_corrections:
        from collections import Counter
        correction_counts = Counter(all_corrections)
        for correction, count in correction_counts.most_common():
            print(f"  • {correction}: {count} times")
    else:
        print("  • No corrections needed - extractions were accurate")
    
    # Assessment
    print(f"\n🏆 ASSESSMENT:")
    if pass_rate >= 80:
        print("✅ EXCELLENT: Target achieved! Ready for production")
    elif pass_rate >= 75:
        print("✅ SUCCESS: Significant improvement, minor refinement needed")
    elif pass_rate >= 60:
        print("⚠️ PROGRESS: Good improvement, needs more work")
    elif pass_rate > 33.3:
        print("⚠️ SOME PROGRESS: Improvement detected but insufficient")
    else:
        print("❌ NO IMPROVEMENT: Further changes required")
    
    print(f"\n📋 NEXT STEPS:")
    if pass_rate >= 75:
        print("  1. Deploy to production with current improvements")
        print("  2. Monitor performance in real-world usage") 
        print("  3. Collect user feedback for fine-tuning")
    else:
        print("  1. Analyze remaining failures")
        print("  2. Refine system prompt further")
        print("  3. Add more specific validation rules")
    
    return {
        "pass_rate": pass_rate,
        "critical_pass_rate": critical_pass_rate,
        "avg_response_time": avg_response_time,
        "corrections_applied": len(all_corrections),
        "success": pass_rate >= 75
    }

async def main():
    """Run the enhanced extraction validation"""
    print("🚀 Starting Enhanced Intent Extraction Validation...")
    results = await test_enhanced_extraction()
    
    # Save results
    results_file = "/Users/cgordon/workstation/n8n-lab/enhanced_extraction_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    if results["success"]:
        print("🎉 SUCCESS: Enhanced intent extraction is ready for production!")
    else:
        print("🔄 NEEDS REFINEMENT: Continue with additional improvements")

if __name__ == "__main__":
    asyncio.run(main())