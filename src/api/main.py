import os
import sys
import time
import logging
import numpy as np
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI
import psycopg2
from psycopg2.extras import RealDictCursor

# Path resolution
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

DB_URL = "postgresql://orqestra_admin:supersecretpassword@db:5432/orqestra"

# NEW: Import our Celery background task instead of the synchronous models
from src.workers.tasks import detect_contradiction_task

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
class CrossSystemRequest(BaseModel):
    system_a: str
    claim_a: str
    system_b: str
    claim_b: str

class AnalysisResponse(BaseModel):
    status: str  
    message: str
    matched_system: Optional[str] = None
    matched_text: Optional[str] = None
    similarity_score: Optional[float] = None
    routing_tier: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    processing_time_ms: Optional[float] = None 

# ==========================================
# APP INITIALIZATION
# ==========================================
app = FastAPI(
    title="Orqestra Core API",
    description="Neuro-Symbolic Cross-System Contradiction Detection",
    version="1.2.0" # Bumped version for Async Architecture
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client for the semantic pre-filter
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_cosine_similarity(text1: str, text2: str) -> float:
    """Uses OpenAI embeddings to check if the claims are semantically related."""
    try:
        response = client.embeddings.create(
            input=[text1, text2],
            model="text-embedding-3-small"
        )
        emb1 = np.array(response.data[0].embedding)
        emb2 = np.array(response.data[1].embedding)
        
        # Cosine similarity formula
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        return 1.0  # Fail open: push to queue if embedding fails

# ==========================================
# API ENDPOINTS
# ==========================================
@app.get("/health")
def health_check():
    return {"status": "online", "engine": "Async Cross-System Triage Active"}

@app.post("/api/v1/analyze", response_model=AnalysisResponse)
def analyze_claim_pair(request: CrossSystemRequest):
    total_start_time = time.time()
    logger.info(f"📥 [INGEST] Cross-System Pair received: '{request.system_a}' vs '{request.system_b}'")
    
    # 1. SEMANTIC PRE-FILTER TIER (OpenAI Embeddings)
    sim_start = time.time()
    similarity = get_cosine_similarity(request.claim_a, request.claim_b)
    sim_latency = (time.time() - sim_start) * 1000
    
    logger.info(f"🔍 [PRE-FILTER] Computed cosine similarity: {similarity:.3f} in {sim_latency:.1f}ms")
    
    if similarity < 0.60:
        total_latency = (time.time() - total_start_time) * 1000
        logger.info(f"✅ [SAFE] Claims are not semantically related. Dropping pair.")
        return AnalysisResponse(
            status="SAFE",
            message="Claims are not semantically related.",
            similarity_score=similarity,
            processing_time_ms=round(total_latency, 2)
        )

    # 2. QUEUE THE HEAVY LIFTING TO CELERY
    logger.info("📡 [QUEUE] Semantic match found. Dispatching to Celery Workers...")
    
    try:
        # Push the task to Redis asynchronously
        detect_contradiction_task.apply_async(
            args=[request.system_a, request.claim_a, request.system_b, request.claim_b, float(similarity)],
            queue='contradiction_detection'
        )
    except Exception as e:
        logger.error(f"❌ Failed to queue task to Celery/Redis: {e}")
        raise HTTPException(status_code=500, detail="Message broker unavailable.")

    # 3. INSTANTLY RETURN PROCESSING STATUS
    total_latency = (time.time() - total_start_time) * 1000
    return AnalysisResponse(
        status="PROCESSING",
        message="Semantic overlap detected. Pair dispatched to async AI workers for full Bouncer/Apex triage.",
        similarity_score=similarity,
        routing_tier="Celery Queue",
        processing_time_ms=round(total_latency, 2)
    )

@app.get("/api/v1/contradictions")
def get_live_contradictions():
    """Fetches the live feed of intercepted contradictions and their AI risk profiles."""
    logger.info("📡 [API] Fetching live contradiction feed for UI...")
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        # RealDictCursor automatically converts PostgreSQL rows into Python dictionaries!
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # The Master Query: Join the contradiction to its claims, systems, and AI explanation
        query = """
            SELECT 
                c.id as contradiction_id,
                c.severity,
                c.confidence_score,
                c.status,
                c.detected_at,
                sa.name as system_a_name,
                ca.object as claim_a_text,
                sb.name as system_b_name,
                cb.object as claim_b_text,
                e.why_they_contradict,
                e.risk_level,
                e.recommended_action
            FROM contradictions c
            JOIN claims ca ON c.claim_a_id = ca.id
            JOIN systems sa ON ca.system_id = sa.id
            JOIN claims cb ON c.claim_b_id = cb.id
            JOIN systems sb ON cb.system_id = sb.id
            LEFT JOIN explanations e ON c.id = e.contradiction_id
            ORDER BY c.detected_at DESC
            LIMIT 50;
        """
        cur.execute(query)
        results = cur.fetchall()
        
        return {"status": "success", "count": len(results), "data": results}
        
    except Exception as e:
        logger.error(f"❌ [API] Failed to fetch database records: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
    finally:
        if conn:
            cur.close()
            conn.close()