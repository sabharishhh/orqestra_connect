# src/workers/contradiction_detector.py
import os
import sys
import logging
import psycopg2
from pgvector.psycopg2 import register_vector
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import dspy

load_dotenv()

# 1. PATH RESOLUTION
worker_dir = Path(__file__).resolve().parent
project_root = worker_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.services.apex import Apex
from src.workers.explainability import process_and_alert  # Connect Worker 1 to Worker 2

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# 2. STATE MANAGEMENT
dspy.settings.configure(cache=False)

# 3. INITIALIZATION
BRAIN_PATH = os.path.join(project_root, "models", "apex_compiled", "optimized_config.json")
DB_URL = "postgresql://orqestra_admin:supersecretpassword@localhost:5432/orqestra"

logger.info("⚙️  Booting Contradiction Detector Worker...")
try:
    judge = Apex(compiled_path=BRAIN_PATH)
except Exception as e:
    logger.error(f"❌ Failed to load Apex brain at {BRAIN_PATH}: {e}")
    sys.exit(1)

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ==========================================
# LIVE DATABASE INTERFACES (pgvector)
# ==========================================
def get_embedding(text):
    """Generate the embedding for the incoming claim."""
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def get_similar_claims_from_db(new_claim_text: str, limit=3, similarity_threshold=0.65):
    """Search the live pgvector database for semantic collisions."""
    logger.info("🧠 Generating vector embedding for incoming claim...")
    new_embedding = get_embedding(new_claim_text)
    
    logger.info("🔍 Searching pgvector for collisions...")
    try:
        conn = psycopg2.connect(DB_URL)
        register_vector(conn)
        cur = conn.cursor()
        
        # pgvector uses `<=>` for cosine distance. Similarity is (1 - distance).
        max_distance = 1.0 - similarity_threshold
        
        cur.execute("""
            SELECT system_name, claim_text, 1 - (embedding <=> %s::vector) AS similarity
            FROM enterprise_claims
            WHERE embedding <=> %s::vector < %s
            ORDER BY similarity DESC
            LIMIT %s
        """, (new_embedding, new_embedding, max_distance, limit))
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        similar_claims = []
        for row in results:
            similar_claims.append({
                "system": row[0],
                "claim_text": row[1],
                "similarity_score": round(row[2], 3)
            })
            
        return similar_claims
        
    except Exception as e:
        logger.error(f"❌ Database query failed: {e}")
        return []

# ==========================================
# THE WORKER TASK
# ==========================================
def check_new_claim(new_system_name: str, new_claim_text: str):
    logger.info(f"\n📥 Ingested from [{new_system_name}]: '{new_claim_text}'")
    
    similar_claims = get_similar_claims_from_db(new_claim_text)
    
    if not similar_claims:
        logger.info("✅ No semantic collisions found in database. Claim is safe.")
        return

    for matched_claim in similar_claims:
        logger.info(f"⚡ Vector collision detected (Score: {matched_claim['similarity_score']}). Routing to Apex...")
        
        try:
            verdict = judge(
                claim_a=new_claim_text, 
                claim_b=matched_claim['claim_text']
            )
        except Exception as e:
            logger.error(f"⚠️ Apex inference failed: {e}. Tagging for retry.")
            continue
        
        raw_relationship = getattr(verdict, 'logical_relationship', 'ERROR')
        relationship = str(raw_relationship).strip().upper()
        reasoning = getattr(verdict, 'reasoning', 'No reasoning provided.')
        
        if relationship == "CONTRADICTION":
            logger.info(f"🚨 Apex confirmed CONTRADICTION! Handing off to Explainability Worker...")
            
            # Dispatch the alert payload synchronously for this test
            process_and_alert(
                system_a=new_system_name,
                claim_a=new_claim_text,
                system_b=matched_claim['system'],
                claim_b=matched_claim['claim_text'],
                reasoning=reasoning
            )
            # Break after finding a contradiction so we don't spam Slack
            break
        else:
            logger.info(f"🛡️  Apex dismissed collision as: {relationship}")
            logger.info(f"   Reasoning: {reasoning}")

# ==========================================
# RUN THE END-TO-END PIPELINE
# ==========================================
if __name__ == "__main__":
    # Test a brand new claim that SHOULD hit our DB!
    # Our DB contains: "Metformin is contraindicated when eGFR falls below 45 mL/min/1.73m²."
    test_claim = "Metformin may be continued at a reduced dose until eGFR drops below 30 mL/min/1.73m²."
    
    check_new_claim(
        new_system_name="ClinicalDecisionSupport_V2",
        new_claim_text=test_claim
    )