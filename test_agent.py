"""
Fluid AI — Test Script
Demonstrates the agent with two test inputs:
1. Standard business request
2. Complex, ambiguous request requiring autonomous decision-making

Usage:
    python test_agent.py
"""

import requests
import json
import sys
import time


BASE_URL = "http://localhost:8000"


def test_health():
    """Verify the server is running."""
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        resp.raise_for_status()
        print("✅ Server is healthy:", resp.json())
        return True
    except requests.ConnectionError:
        print("❌ Server is not running. Start it with: uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def run_agent(request_text: str, label: str) -> dict | None:
    """Send a request to the agent and display results."""
    print("\n" + "=" * 70)
    print(f"📋 TEST: {label}")
    print("=" * 70)
    print(f"Request: {request_text[:100]}...")
    print("-" * 70)

    start = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/agent",
            json={"request": request_text},
            timeout=300,  # 5 min timeout for complex tasks
        )
        elapsed = time.time() - start

        if resp.status_code != 200:
            print(f"❌ Error ({resp.status_code}): {resp.text}")
            return None

        data = resp.json()

        # Display results
        print(f"\n⏱️  Completed in {elapsed:.1f}s")
        print(f"📊 Status: {data['status']}")
        print(f"\n📋 Execution Plan: {data['execution_plan']['document_title']}")
        print(f"   Document Type: {data['execution_plan']['document_type']}")
        print(f"   Reasoning: {data['execution_plan']['reasoning'][:150]}...")
        print(f"   Steps: {len(data['execution_plan']['steps'])}")

        for step in data["execution_plan"]["steps"]:
            print(f"     {step['step_number']}. [{step['step_type']}] {step['title']}")

        print(f"\n⚡ Step Results:")
        for result in data["step_results"]:
            status_icon = "✅" if result["status"] == "completed" else "❌"
            retries = f" (retries: {result['retries_used']})" if result["retries_used"] > 0 else ""
            content_preview = result["content"][:80] + "..." if result["content"] else "No content"
            print(f"   {status_icon} Step {result['step_number']}: {result['title']}{retries}")
            print(f"      Preview: {content_preview}")

        if data.get("reflection"):
            ref = data["reflection"]
            print(f"\n🔍 Quality Review:")
            print(f"   Score: {ref['quality_score']}/10")
            print(f"   Completeness: {ref['completeness'][:100]}...")
            print(f"   Coherence: {ref['coherence'][:100]}...")
            if ref.get("improvements"):
                print(f"   Improvements suggested: {len(ref['improvements'])}")
                for imp in ref["improvements"][:3]:
                    print(f"     • {imp[:80]}...")

        print(f"\n📄 Document: {data.get('document_path', 'N/A')}")
        print(f"   Download: {BASE_URL}{data.get('document_download_url', '')}")
        print(f"\n📝 Summary: {data['summary']}")

        return data

    except requests.Timeout:
        print(f"❌ Request timed out after {time.time() - start:.1f}s")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Run both test cases."""
    print("🚀 Fluid AI — Agent Test Suite")
    print("=" * 70)

    # Health check
    if not test_health():
        sys.exit(1)

    # ── Test 1: Standard Business Request ────────────────────────────
    test1_request = (
        "Create a project plan for developing a mobile app for a local restaurant, "
        "including timeline, budget estimates, and team requirements."
    )

    result1 = run_agent(test1_request, "Standard Business Request — Mobile App Project Plan")

    # ── Test 2: Complex / Ambiguous Request ──────────────────────────
    test2_request = (
        "Our company is merging with a competitor. Draft a comprehensive integration "
        "plan covering IT systems consolidation, employee onboarding from both sides, "
        "brand unification strategy, and risk mitigation. We have 500 employees and "
        "they have 300. The merger needs to be completed within 18 months. We're in "
        "the fintech space and both companies have different tech stacks."
    )

    result2 = run_agent(test2_request, "Complex Request — Corporate Merger Integration Plan")

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Test 1 (Standard): {'✅ PASSED' if result1 and result1['status'] in ('success', 'partial_failure') else '❌ FAILED'}")
    print(f"Test 2 (Complex):  {'✅ PASSED' if result2 and result2['status'] in ('success', 'partial_failure') else '❌ FAILED'}")

    if result1:
        print(f"\n📄 Document 1: {result1.get('document_path', 'N/A')}")
    if result2:
        print(f"📄 Document 2: {result2.get('document_path', 'N/A')}")


if __name__ == "__main__":
    main()
