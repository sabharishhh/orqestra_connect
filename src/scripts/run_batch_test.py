# src/scripts/run_batch_test.py
import os
import sys
import time
from pathlib import Path

# Path resolution
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import your Golden Seed dataset
from dataset.orqestra_50 import train_set

# Import the initialized Bouncer, Judge, and DB logic from your worker
from src.workers.contradiction_detector import (
    bouncer, 
    judge, 
    get_similar_claims_from_db
)

def run_evaluation():
    print("\n" + "="*50)
    print("🚀 STARTING ORQESTRA BATCH PIPELINE TEST (50 CLAIMS)")
    print("="*50 + "\n")

    stats = {
        "total": len(train_set),
        "correct": 0,
        "bouncer_intercepts": 0,
        "apex_escalations": 0,
        "missed_retrievals": 0,
        "errors": 0
    }

    start_time = time.time()

    for i, example in enumerate(train_set):
        incoming_claim = example.claim_b
        ground_truth = example.logical_relationship.strip().upper()
        
        print(f"\n[{i+1}/50] Testing Target: {ground_truth}")
        
        # 1. TEST RETRIEVAL (pgvector)
        candidates = get_similar_claims_from_db(
            new_system_name="BatchTester", 
            new_claim_text=incoming_claim, 
            limit=1
        )
        
        if not candidates:
            print("   ❌ FAILED: pgvector found no matches.")
            stats["missed_retrievals"] += 1
            continue
            
        matched_text = candidates[0]['claim_text']
        
        # 2. TEST BOUNCER (DeBERTa)
        try:
            b_verdict = bouncer.evaluate_pair(incoming_claim, matched_text)
            pred_label = b_verdict["prediction"]
            conf = b_verdict["confidence"]
            
            # Map Bouncer labels safely
            is_contradict = pred_label in ["CONTRADICTION", "CONTRADICT"]
            is_neutral = pred_label in ["NEUTRAL", "ENTAILMENT"]
            
            final_verdict = None
            
            if conf >= 0.95:
                stats["bouncer_intercepts"] += 1
                final_verdict = "CONTRADICTION" if is_contradict else "NEUTRAL"
                print(f"   🛡️  BOUNCER INTERCEPT: {final_verdict} (Conf: {conf:.3f})")
            else:
                # 3. TEST JUDGE (Apex/LLM)
                stats["apex_escalations"] += 1
                print(f"   ⚖️  ESCALATED TO APEX (Bouncer Conf: {conf:.3f})")
                
                a_verdict = judge(claim_a=incoming_claim, claim_b=matched_text)
                raw_rel = getattr(a_verdict, 'logical_relationship', 'ERROR').strip().upper()
                final_verdict = "CONTRADICTION" if raw_rel == "CONTRADICTION" else "NEUTRAL"
                
                print(f"   🧠 APEX VERDICT: {final_verdict}")

            # 4. EVALUATE ACCURACY
            # Note: For this binary risk test, Entailment and Neutral are both "Safe/NEUTRAL"
            mapped_truth = "CONTRADICTION" if ground_truth == "CONTRADICTION" else "NEUTRAL"
            
            if final_verdict == mapped_truth:
                print("   ✅ MATCH: Correctly Classified.")
                stats["correct"] += 1
            else:
                print(f"   ❌ MISMATCH: Predicted {final_verdict}, but truth was {mapped_truth}.")
                
        except Exception as e:
            print(f"   ⚠️ ERROR on iteration {i+1}: {e}")
            stats["errors"] += 1

    # ==========================================
    # FINAL REPORT GENERATION
    # ==========================================
    end_time = time.time()
    accuracy = (stats["correct"] / stats["total"]) * 100
    cost_savings = (stats["bouncer_intercepts"] / stats["total"]) * 100
    
    print("\n\n" + "="*50)
    print("📊 ORQESTRA PIPELINE METRICS REPORT")
    print("="*50)
    print(f"Time Elapsed:         {end_time - start_time:.1f} seconds")
    print(f"Total Claims Tested:  {stats['total']}")
    print(f"Correctly Assessed:   {stats['correct']}")
    print(f"Overall Accuracy:     {accuracy:.1f}%\n")
    
    print("💸 EFFICIENCY & ROUTING METRICS")
    print(f"Bouncer Intercepts:   {stats['bouncer_intercepts']} ({cost_savings:.1f}% API Cost Saved)")
    print(f"Apex Escalations:     {stats['apex_escalations']} (Sent to LLM)")
    print(f"Missed Retrievals:    {stats['missed_retrievals']} (pgvector failed to find)")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_evaluation()