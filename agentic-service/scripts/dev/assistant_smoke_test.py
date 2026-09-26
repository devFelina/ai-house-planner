from __future__ import annotations
"""End-to-end test: LLM interpretation → deterministic feasibility engine."""
import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.architecture_assistant import interpret_user_message

messages = [
    ("Design me a 4 bedroom two floor modern house on 25 perch land", "DESIGN_REQUEST"),
    ("I have 25 perch land. How many bedrooms are suitable?", "LAND_FEASIBILITY_ADVICE"),
    ("Design me a 6 bedroom single floor house on 3 perch land", "DESIGN_REQUEST"),
]

for msg, expected_intent in messages:
    print(f"\n{'='*60}")
    print(f"INPUT: {msg}")
    print(f"EXPECTED INTENT: {expected_intent}")
    print('='*60)
    
    result = interpret_user_message(msg)
    intent = result.get('intent', 'UNKNOWN')
    print(f"ACTUAL INTENT: {intent}")
    
    if intent == 'DESIGN_REQUEST' and result.get('action') and 'feasibility' in result['action'].get('payload', {}):
        f = result['action']['payload']['feasibility']
        print(f"  can_proceed: {f['can_proceed']}")
        print(f"  compatible_plan_count: {f['compatible_plan_count']}")
        print(f"  reason_codes: {f['reason_codes']}")
        print(f"  suggestions: {f['suggestions']}")
        print(f"  land: {json.dumps(f.get('land'), indent=2)}")
    
    # We didn't explicitly include feasibility_advice in the action payload for LAND_FEASIBILITY_ADVICE, 
    # but we included it in context_str. For test purposes, let's just print the reply.
    elif intent == 'LAND_FEASIBILITY_ADVICE':
        print(f"  reply message:\n    {result['reply']}")
    
    print()

print("E2E TESTS COMPLETE ✓")
