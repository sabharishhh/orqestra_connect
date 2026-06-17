import sys
import os
import json
import time
import requests
import logging
from pathlib import Path

# Path resolution
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.healthtrack.agents import guidelines_agent, med_review_agent
from src.healthtrack.claim_extractor import extract_claims

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Pipeline")

ORQESTRA_API_URL = "http://localhost:8000/api/v1/analyze"

def run_automated_pipeline():
    logger.info("🚀 Booting HealthTrack -> Orqestra Automated Pipeline")
    
    # 1. Load the probes
    probe_path = os.path.join(project_root, "src", "healthtrack", "data", "probes.json")
    with open(probe_path, "r") as f:
        probes = json.load(f)
        
    probe = probes[0] # Let's just run HC-001 (Metformin) for now
    logger.info(f"\n📝 Running Probe: {probe['id']}")
    
    # 2. Query the Agents
    logger.info(f"🤖 Generating response from {guidelines_agent.name}...")
    output_a = guidelines_agent.analyze(probe["patient_profile"])
    
    logger.info(f"🤖 Generating response from {med_review_agent.name}...")
    output_b = med_review_agent.analyze(probe["patient_profile"])
    
    # 3. Extract Discrete Claims
    logger.info("\n🧬 Extracting claims via LLM...")
    claims_a = extract_claims(output_a)
    claims_b = extract_claims(output_b)
    
    primary_claim_a = claims_a[0] if claims_a else output_a
    primary_claim_b = claims_b[0] if claims_b else output_b
    
    logger.info(f"   Agent A Claim: {primary_claim_a}")
    logger.info(f"   Agent B Claim: {primary_claim_b}")
    
    # 4. Fire to Orqestra API
    logger.info("\n📡 Blasting cross-system pair to Docker Orqestra API...")
    payload = {
        "system_a": guidelines_agent.name,
        "claim_a": primary_claim_a,
        "system_b": med_review_agent.name,
        "claim_b": primary_claim_b
    }
    
    start_time = time.time()
    try:
        response = requests.post(ORQESTRA_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        
        latency = (time.time() - start_time) * 1000
        
        logger.info("\n==========================================")
        logger.info(f"🏁 ORQESTRA ENGINE VERDICT ({latency:.0f}ms)")
        logger.info("==========================================")
        logger.info(f"Status:     {result.get('status')}")
        logger.info(f"Message:    {result.get('message')}")
        logger.info(f"Tier:       {result.get('routing_tier')}")
        if result.get('confidence'):
            logger.info(f"Confidence: {result.get('confidence')*100:.1f}%")
        logger.info(f"Reasoning:  {result.get('reasoning')}")
        logger.info("==========================================\n")
        
    except requests.exceptions.ConnectionError:
        logger.error("❌ Failed to connect to Orqestra API. Is Docker running?")
    except Exception as e:
        logger.error(f"❌ API Request failed: {e}")

if __name__ == "__main__":
    run_automated_pipeline()