# src/workers/contradiction_detector.py
import os
import sys
import logging
import hashlib
import psycopg2
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

# 1. SYSTEM PATH RESOLUTION
worker_dir = Path(__file__).resolve().parent
project_root = worker_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Initialize formal logic frameworks safely
import dspy
dspy.settings.configure(cache=False)

from src.services.apex import Apex
from src.workers.explainability import process_and_alert

# 2. LOGGING CONFIGURATION
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Orqestra.ContradictionDetector")

# 3. ENVIRONMENT & STATE VARIABLES
BRAIN_PATH = os.path.join(project_root, "models", "apex_compiled", "optimized_config.json")
DB_URL = os.environ.get("DATABASE_URL", "postgresql://orqestra_admin:supersecretpassword@localhost:5432/orqestra")
BOUNCER_MODEL_NAME = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"

# 4. LAZY INITIALIZATION CONTAINER FOR LOCAL TRANSFORMERS
class LocalBouncerContainer:
    """Lazily allocates machine resources for local cross-encoder classification."""
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._tokenizer = None
        self._model = None
        self._torch = None

    def _load(self):
        if self._model is not None:
            return
        
        logger.info("📥 Loading local DeBERTa cross-encoder onto memory tier...")
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            self._torch = torch
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            
            # Utilize execution optimizations if target system provides accelerators
            if self._torch.cuda.is_available():
                self._model = self._model.to("cuda")
                logger.info("⚡ Accelerator found. Bouncer bound to CUDA runtime context.")
            else:
                logger.info("🛡️  No accelerator found. Bouncer running on local CPU thread context.")
        except ImportError as env_err:
            logger.error(f"❌ Missing critical processing dependencies: {env_err}")
            raise env_err

    def evaluate_pair(self, text_a: str, text_b: str) -> Dict[str, Any]:
        """Executes zero-shot NLI token array classification on the pair."""
        self._load()
        
        # Explicit pair concatenation for cross-encoder ingestion signatures
        inputs = self._tokenizer(
            text_a, 
            text_b, 
            padding=True, 
            truncation=True, 
            max_length=512, 
            return_tensors="pt"
        )
        
        if self._torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with self._torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits[0]
            probabilities = self._torch.softmax(logits, dim=0).tolist()

        # Dynamic out-of-the-box configuration mapping
        label_mapping = self._model.config.label2id
        id_mapping = {v: k.upper() for k, v in label_mapping.items()}
        
        # Safe fallback standard indexing if configuration layers contain drift variations
        if len(probabilities) == 3 and not any(k in ["CONTRADICTION", "ENTAILMENT", "NEUTRAL"] for k in id_mapping.values()):
            id_mapping = {0: "ENTAILMENT", 1: "NEUTRAL", 2: "CONTRADICTION"}

        prob_dict = {id_mapping.get(i, f"LABEL_{i}"): prob for i, prob in enumerate(probabilities)}
        
        # Resolve top dominant class configuration text
        max_idx = probabilities.index(max(probabilities))
        pred_label = id_mapping.get(max_idx, "UNKNOWN")
        confidence = probabilities[max_idx]

        return {
            "prediction": pred_label,
            "confidence": confidence,
            "all_probabilities": prob_dict
        }

# Instantiate singleton lazy container reference
bouncer = LocalBouncerContainer(model_name=BOUNCER_MODEL_NAME)
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    logger.info("⚙️  Configuring Neuro-Symbolic Arbitration Runtime...")
    judge = Apex(compiled_path=BRAIN_PATH)
    logger.info("🧠 Apex Logic Engine successfully mapped onto compiled brain.")
except Exception as e:
    logger.error(f"❌ Critical initialization failure: Unable to map Apex runtime context: {e}")
    sys.exit(1)

# 5. DATA TRANSMISSION MIDDLEWARE
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception))
)
def generate_vector_embedding(text: str) -> List[float]:
    """Generates a dense vector representation using the target enterprise spec."""
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def get_similar_claims_from_db(new_system_name: str, new_claim_text: str, limit: int = 5, similarity_threshold: float = 0.50) -> List[Dict[str, Any]]:
    """Queries the live database layer to isolate spatial text collisions."""
    try:
        new_embedding = generate_vector_embedding(new_claim_text)
    except Exception as e:
        logger.error(f"❌ Spatial representation layer failed to translate asset text: {e}")
        return []

    similar_claims = []
    conn = None
    try:
        from pgvector.psycopg2 import register_vector
        conn = psycopg2.connect(DB_URL)
        register_vector(conn)
        cur = conn.cursor()
        
        max_distance = 1.0 - similarity_threshold
        
        # Filter isolates cross-system assertions, avoiding self-collisions from the originating system.
        cur.execute("""
            SELECT system_name, claim_text, 1 - (embedding <=> %s::vector) AS similarity
            FROM enterprise_claims
            WHERE embedding <=> %s::vector < %s
              AND system_name != %s
            ORDER BY similarity DESC
            LIMIT %s
        """, (new_embedding, new_embedding, max_distance, new_system_name, limit))
        
        rows = cur.fetchall()
        for row in rows:
            similar_claims.append({
                "system": row[0],
                "claim_text": row[1],
                "similarity_score": round(row[2], 3)
            })
            
        cur.close()
    except Exception as db_err:
        logger.error(f"❌ Database querying context failed down-level execution: {db_err}")
    finally:
        if conn:
            conn.close()
            
    return similar_claims

# 6. PIPELINE ORCHESTRATION LOGIC
def check_new_claim(new_system_name: str, new_claim_text: str):
    """Orchestrates the complete Triage Cascade pipeline logic execution workflow."""
    logger.info(f"📥 Processing incoming semantic stream from [{new_system_name}]")
    
    # Tier 1 Lookup: pgvector database search
    candidates = get_similar_claims_from_db(new_system_name, new_claim_text)
    if not candidates:
        logger.info("✅ Core filter clean: No cross-system spatial vector overlaps isolated.")
        return

    for candidate in candidates:
        matched_system = candidate["system"]
        matched_text = candidate["claim_text"]
        v_score = candidate["similarity_score"]
        
        logger.info(f"⚡ Vector overlap isolated with [{matched_system}] (Spatial Similarity: {v_score})")
        
        # Tier 2 Lookup: Local Bouncer (Cross-Encoder zero-shot NLI)
        try:
            bouncer_verdict = bouncer.evaluate_pair(new_claim_text, matched_text)
            pred_label = bouncer_verdict["prediction"]
            confidence = bouncer_verdict["confidence"]
            probs = bouncer_verdict["all_probabilities"]
            
            # Transform label values cleanly to standardize evaluation branches
            is_contradiction_match = (pred_label in ["CONTRADICTION", "CONTRADICT"])
            is_neutral_match = (pred_label in ["NEUTRAL", "ENTAILMENT"])
            
            logger.info(f"🕵️  Local Bouncer Inference: Derived relationship '{pred_label}' at confidence level: {confidence:.4f}")
            
            # Cascade Routing Branch 1: Unambiguous Interception (>95% Confidence)
            if confidence >= 0.995:
                if is_contradiction_match:
                    logger.info("🚨 Local Bouncer intercepted absolute contradiction! High confidence execution route triggered.")
                    process_and_alert(
                        system_a=new_system_name,
                        claim_a=new_claim_text,
                        system_b=matched_system,
                        claim_b=matched_text,
                        reasoning=f"[INTERCEPTED AT BOUNCER]: Local DeBERTa model flagged absolute logical contradiction with 95%+ classification certainty. (Confidence: {confidence:.4f})"
                    )
                    break
                elif is_neutral_match:
                    logger.info(f"🛡️  Local Bouncer dismissed vector match safely for $0 API cost. (Confidence: {confidence:.4f})")
                    continue
            
            # Cascade Routing Branch 2: Escalate to the Supreme Court Engine (The Confusion Zone)
            logger.info("⚖️  Collision metrics indeterminate inside middleware tier. Escalating case to Apex Supreme Court Engine...")
            
            try:
                verdict = judge(claim_a=new_claim_text, claim_b=matched_text)
                raw_relationship = getattr(verdict, 'logical_relationship', 'ERROR')
                relationship = str(raw_relationship).strip().upper()
                reasoning = getattr(verdict, 'reasoning', 'No structural engine reasoning extracted.')
                
                if relationship in ["CONTRADICTION", "CONTRADICT"]:
                    logger.info(f"🚨 Apex Engine confirmed critical collision constraint violation. Handing payload off to tracking listeners...")
                    process_and_alert(
                        system_a=new_system_name,
                        claim_a=new_claim_text,
                        system_b=matched_system,
                        claim_b=matched_text,
                        reasoning=reasoning
                    )
                    break
                else:
                    logger.info(f"🛡️  Apex Engine successfully cleared asset overlap verification. Verdict: {relationship}")
                    
            except Exception as apex_err:
                logger.error(f"⚠️ Arbitrator inference execution layer faulted unexpectedly: {apex_err}")
                continue

        except Exception as bouncer_err:
            logger.critical(f"❌ Local processing pipeline layer execution fault: {bouncer_err}. Dropping out of cascade.")
            continue

# 7. EXECUTABLE DEMO PROFILE RUNNER
if __name__ == "__main__":
    # Standard standalone check verifying script logic validation rules
    logger.info("🧪 Initializing isolated sanity run verifying pipeline cascade metrics...")
    
    # Mocking standard processing environment fallback contexts
    test_claim = "Metformin therapy must be immediately discontinued if the patient's eGFR measurement profile drops beneath a 45 mL/min boundary metric."
    check_new_claim(
        new_system_name=" CDS_Engine_Beta",
        new_claim_text=test_claim
    )