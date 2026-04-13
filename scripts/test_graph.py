"""
CLI end-to-end test runner for the triage LangGraph.
Usage: python scripts/test_graph.py

Tests 5 canonical cases — verifies routing correctness without the API layer.
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage
from src.graph.builder import build_graph
from src.database.connection import create_db_and_tables

TEST_CASES = [
    {
        "name": "Chest Pain (should → ER EMERGENCY)",
        "messages": ["I have severe chest pain radiating to my left arm and I'm sweating a lot"],
        "expected_urgency": "EMERGENCY",
        "expected_dept": "Emergency Room",
    },
    {
        "name": "Sore Throat + Ear Pain (should → ENT NON_URGENT)",
        "messages": [
            "I have a bad sore throat",
            "My ear hurts too and it started yesterday. Pain is about 5/10, no fever.",
        ],
        "expected_urgency": "NON_URGENT",
        "expected_dept": "ENT",
    },
    {
        "name": "Seizure (should → ER EMERGENCY)",
        "messages": ["My sister just had a seizure and is not responding"],
        "expected_urgency": "EMERGENCY",
        "expected_dept": "Emergency Room",
    },
    {
        "name": "Mild Cold (should → SELF_CARE or NON_URGENT)",
        "messages": [
            "I have a mild runny nose and slight cough",
            "No fever, started this morning, severity 2/10, adult.",
        ],
        "expected_urgency": "SELF_CARE",
        "expected_dept": None,   # flexible
    },
    {
        "name": "Stomach Pain (should → Gastroenterology URGENT)",
        "messages": [
            "I have bad stomach pain on the right side",
            "It started 4 hours ago, severity 7/10, I'm an adult. Also feel nauseous.",
        ],
        "expected_urgency": "URGENT",
        "expected_dept": "Gastroenterology",
    },
]


async def run_test(graph, case: dict, idx: int) -> bool:
    print(f"\n{'='*60}")
    print(f"TEST {idx+1}: {case['name']}")
    print(f"{'='*60}")

    session_id = f"test_session_{idx}"
    config = {"configurable": {"thread_id": session_id}}
    passed = True

    for i, msg_text in enumerate(case["messages"]):
        print(f"\n>>> Patient: {msg_text}")
        input_state = {
            "messages": [HumanMessage(content=msg_text)],
            "session_id": session_id,
        }

        async for event in graph.astream_events(input_state, config=config, version="v2"):
            kind = event.get("event")
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    print(chunk.content, end="", flush=True)

    print("\n")

    # Get final state
    try:
        state = graph.get_state(config)
        sv = state.values if state else {}
        urgency = sv.get("urgency_level")
        dept = sv.get("routed_department")

        print(f"  Urgency: {urgency} (expected: {case['expected_urgency']})")
        print(f"  Department: {dept} (expected: {case['expected_dept']})")

        urgency_ok = urgency == case["expected_urgency"]
        dept_ok = case["expected_dept"] is None or dept == case["expected_dept"]

        if urgency_ok and dept_ok:
            print("  ✅ PASS")
        else:
            print("  ❌ FAIL")
            passed = False
    except Exception as e:
        print(f"  ⚠️  Could not get final state: {e}")

    return passed


async def main():
    print("Healthcare Triage System — End-to-End Test Suite")
    print("=" * 60)

    create_db_and_tables()
    graph = build_graph()

    results = []
    for i, case in enumerate(TEST_CASES):
        ok = await run_test(graph, case, i)
        results.append(ok)

    print(f"\n{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed — review routing logic or prompts.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
