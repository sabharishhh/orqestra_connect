# src/api/main.py
import sys
import time
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

# Path resolution
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.workers.contradiction_detector import (
    get_similar_claims_from_db, 
    bouncer, 
    judge
)
from src.workers.explainability import process_and_alert

# ==========================================
# ENTERPRISE LOGGING CONFIGURATION
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Orqestra.API")

# ==========================================
# PYDANTIC DATA MODELS
# ==========================================
class ClaimRequest(BaseModel):
    system_name: str
    claim_text: str

class AnalysisResponse(BaseModel):
    status: str  
    message: str
    matched_system: Optional[str] = None
    matched_text: Optional[str] = None
    similarity_score: Optional[float] = None
    routing_tier: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    processing_time_ms: Optional[float] = None  # NEW: Telemetry added to response

# ==========================================
# APP INITIALIZATION
# ==========================================
app = FastAPI(
    title="Orqestra Core API",
    description="Neuro-Symbolic Contradiction Detection Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# API ENDPOINTS
# ==========================================
@app.get("/health")
def health_check():
    return {"status": "online", "engine": "Triage Cascade Active"}

@app.post("/api/v1/analyze", response_model=AnalysisResponse)
def analyze_claim(request: ClaimRequest, background_tasks: BackgroundTasks):
    total_start_time = time.time()
    logger.info(f"📥 [INGEST] Request received from system: '{request.system_name}'")
    
    # 1. RETRIEVAL TIER (Database)
    db_start = time.time()
    candidates = get_similar_claims_from_db(
        new_system_name=request.system_name, 
        new_claim_text=request.claim_text,
        limit=3,
        similarity_threshold=0.50 
    )
    db_latency = (time.time() - db_start) * 1000
    logger.info(f"🔍 [pgvector] Found {len(candidates)} candidates in {db_latency:.1f}ms")
    
    if not candidates:
        total_latency = (time.time() - total_start_time) * 1000
        logger.info(f"✅ [SAFE] No semantic overlaps. Request completed in {total_latency:.1f}ms")
        return AnalysisResponse(
            status="SAFE",
            message="No semantic overlaps found in the database.",
            processing_time_ms=round(total_latency, 2)
        )

    for i, candidate in enumerate(candidates):
        matched_text = candidate['claim_text']
        matched_sys = candidate['system']
        sim_score = candidate['similarity_score']
        
        logger.info(f"⚙️  Evaluating Candidate {i+1}/{len(candidates)} (Sim: {sim_score:.3f} | System: {matched_sys})")
        
        # 2. BOUNCER TIER (Local NLI)
        bouncer_start = time.time()
        try:
            b_verdict = bouncer.evaluate_pair(request.claim_text, matched_text)
            bouncer_latency = (time.time() - bouncer_start) * 1000
            
            pred_label = b_verdict["prediction"]
            conf = b_verdict["confidence"]
            
            is_contradict = pred_label in ["CONTRADICTION", "CONTRADICT"]
            is_neutral = pred_label in ["NEUTRAL", "ENTAILMENT"]
            
            logger.info(f"🕵️  [BOUNCER] Predicted: {pred_label} (Conf: {conf:.4f}) in {bouncer_latency:.1f}ms")
            
            # BOUNCER HIGH-CONFIDENCE BRANCH
            if conf >= 0.995:
                if is_contradict:
                    reasoning = f"[BOUNCER INTERCEPT]: Absolute logical contradiction flagged with {conf:.4f} confidence."
                    logger.warning(f"🚨 [ALERT] Bouncer intercepted contradiction! Skipping LLM.")
                    
                    background_tasks.add_task(
                        process_and_alert, request.system_name, request.claim_text, matched_sys, matched_text, reasoning
                    )
                    
                    total_latency = (time.time() - total_start_time) * 1000
                    return AnalysisResponse(
                        status="BOUNCER_INTERCEPT",
                        message="Contradiction intercepted by local filter.",
                        matched_system=matched_sys,
                        matched_text=matched_text,
                        similarity_score=sim_score,
                        routing_tier="DeBERTa Local",
                        confidence=conf,
                        reasoning=reasoning,
                        processing_time_ms=round(total_latency, 2)
                    )
                elif is_neutral:
                    logger.info("🛡️  [SAFE] Bouncer dismissed candidate safely. Moving to next candidate.")
                    continue 
            
            # 3. APEX TIER (Escalation to LLM)
            logger.info(f"⚖️  [ESCALATION] Bouncer unsure (Conf: {conf:.4f}). Escalating to Apex LLM...")
            apex_start = time.time()
            
            a_verdict = judge(claim_a=request.claim_text, claim_b=matched_text)
            apex_latency = (time.time() - apex_start) * 1000
            
            raw_rel = getattr(a_verdict, 'logical_relationship', 'ERROR').strip().upper()
            apex_reasoning = getattr(a_verdict, 'reasoning', 'No reasoning provided.')
            
            logger.info(f"🧠 [APEX] Verdict: {raw_rel} in {apex_latency:.1f}ms")
            
            if raw_rel in ["CONTRADICTION", "CONTRADICT"]:
                logger.warning(f"🚨 [ALERT] Apex confirmed contradiction!")
                
                background_tasks.add_task(
                    process_and_alert, request.system_name, request.claim_text, matched_sys, matched_text, apex_reasoning
                )
                
                total_latency = (time.time() - total_start_time) * 1000
                return AnalysisResponse(
                    status="APEX_CONTRADICTION",
                    message="Contradiction confirmed by Supreme Court Engine.",
                    matched_system=matched_sys,
                    matched_text=matched_text,
                    similarity_score=sim_score,
                    routing_tier="Apex LLM",
                    reasoning=apex_reasoning,
                    processing_time_ms=round(total_latency, 2)
                )
                
        except Exception as e:
            logger.error(f"⚠️ [API] Pipeline error on candidate evaluation: {e}")
            continue

    total_latency = (time.time() - total_start_time) * 1000
    logger.info(f"✅ [SAFE] All candidates cleared. Request completed in {total_latency:.1f}ms")
    return AnalysisResponse(
        status="SAFE",
        message="Semantic overlaps found, but Bouncer and Apex cleared them as safe.",
        routing_tier="Multi-Stage Check",
        processing_time_ms=round(total_latency, 2)
    )