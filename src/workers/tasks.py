import os
import time
import psycopg2
import logging
from src.workers.celery_app import celery_app

logger = logging.getLogger("Celery.Tasks")
DB_URL = os.environ.get("DATABASE_URL", "postgresql://orqestra_admin:supersecretpassword@db:5432/orqestra")

@celery_app.task(name="src.workers.tasks.detect_contradiction", bind=True)
def detect_contradiction_task(self, system_a: str, claim_a: str, system_b: str, claim_b: str, similarity_score: float):
    # ---------------------------------------------------------
    # THE FIX: Import the heavy AI models ONLY when the Celery
    # worker actually executes the task. The API never runs this!
    # ---------------------------------------------------------
    from src.workers.contradiction_detector import bouncer, judge

    logger.info(f"🧵 [CELERY WORKER] Picked up cross-system pair: {system_a} vs {system_b}")
    start_time = time.time()
    
    try:
        # 1. BOUNCER TIER
        b_verdict = bouncer.evaluate_pair(claim_a, claim_b)
        conf = b_verdict["confidence"]
        pred_label = b_verdict["prediction"]
        is_contradict = pred_label in ["CONTRADICTION", "CONTRADICT"]
        
        severity = "HIGH"
        final_status = "SAFE"
        reasoning = "Cleared by local filter."

        if conf >= 0.98 and is_contradict:
            logger.warning(f"🚨 [CELERY] Bouncer Intercept! Confidence: {conf:.4f}")
            final_status = "BOUNCER_INTERCEPT"
            reasoning = f"[BOUNCER INTERCEPT]: Absolute logical contradiction flagged with {conf:.4f} confidence."
        
        # 2. APEX TIER (Escalation)
        elif conf < 0.98 and not is_contradict:
            logger.info("⚖️  [CELERY] Escalating to Apex LLM Judge...")
            a_verdict = judge(claim_a=claim_a, claim_b=claim_b)
            raw_rel = getattr(a_verdict, 'logical_relationship', 'ERROR').strip().upper()
            
            if raw_rel in ["CONTRADICTION", "CONTRADICT"]:
                logger.warning("🚨 [CELERY] Apex confirmed contradiction!")
                final_status = "APEX_CONTRADICTION"
                reasoning = getattr(a_verdict, 'reasoning', 'Apex confirmed contradiction.')
                conf = 0.95 

        # 3. SAVE TO DATABASE
        if final_status != "SAFE":
            _save_contradiction_to_db(system_a, claim_a, system_b, claim_b, severity, conf, reasoning)
            
        latency = (time.time() - start_time) * 1000
        logger.info(f"✅ [CELERY] Task completed in {latency:.0f}ms. Status: {final_status}")
        return {"status": final_status, "processing_time_ms": latency}

    except Exception as e:
        logger.error(f"❌ [CELERY] Task failed: {e}")
        self.retry(exc=e, countdown=5, max_retries=3)


def _save_contradiction_to_db(sys_a, claim_a, sys_b, claim_b, severity, confidence, reasoning):
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        cur.execute("INSERT INTO systems (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET last_seen = CURRENT_TIMESTAMP RETURNING id;", (sys_a,))
        sys_a_id = cur.fetchone()[0]
        
        cur.execute("INSERT INTO systems (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET last_seen = CURRENT_TIMESTAMP RETURNING id;", (sys_b,))
        sys_b_id = cur.fetchone()[0]

        cur.execute("INSERT INTO claims (system_id, subject, predicate, object) VALUES (%s, 'Subject', 'Predicate', %s) RETURNING id;", (sys_a_id, claim_a))
        claim_a_id = cur.fetchone()[0]
        
        cur.execute("INSERT INTO claims (system_id, subject, predicate, object) VALUES (%s, 'Subject', 'Predicate', %s) RETURNING id;", (sys_b_id, claim_b))
        claim_b_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO contradictions (claim_a_id, claim_b_id, severity, confidence_score) 
            VALUES (%s, %s, %s, %s) RETURNING id;
        """, (claim_a_id, claim_b_id, severity, confidence))
        contradiction_id = cur.fetchone()[0]
        
        # Initial placeholder explanation directly from the Bouncer/Apex
        cur.execute("""
            INSERT INTO explanations (contradiction_id, why_they_contradict, risk_level) 
            VALUES (%s, %s, %s);
        """, (contradiction_id, reasoning, "CRITICAL"))

        # ---------------------------------------------------------
        # ADDED: Hand off to the Explainability queue
        # ---------------------------------------------------------
        from src.workers.explainability import generate_explanation_task
        generate_explanation_task.apply_async(
            args=[str(contradiction_id), sys_a, claim_a, sys_b, claim_b, reasoning],
            queue='explainability'
        )

        conn.commit()
        logger.info(f"💾 [DATABASE] Successfully saved Contradiction {contradiction_id} to pgvector and triggered Explainer.")
        
    except Exception as e:
        logger.error(f"Failed to save to database: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()