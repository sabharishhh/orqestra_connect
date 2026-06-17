import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# 1. SYSTEM PATH RESOLUTION
worker_dir = Path(__file__).resolve().parent
project_root = worker_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Initialize formal logic frameworks safely
import dspy
dspy.settings.configure(cache=False)

from src.services.apex import Apex

# 2. LOGGING CONFIGURATION
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Orqestra.ContradictionDetector")

# 3. ENVIRONMENT & STATE VARIABLES
BRAIN_PATH = os.path.join(project_root, "models", "apex_compiled", "optimized_config.json")
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

# ==========================================
# 5. INITIALIZE EXPORTED SINGLETONS
# ==========================================
# Instantiate singleton lazy container reference
bouncer = LocalBouncerContainer(model_name=BOUNCER_MODEL_NAME)

try:
    logger.info("⚙️  Configuring Neuro-Symbolic Arbitration Runtime...")
    _apex_instance = Apex(compiled_path=BRAIN_PATH)
    logger.info("🧠 Apex Logic Engine successfully mapped onto compiled brain.")
except Exception as e:
    logger.error(f"❌ Critical initialization failure: Unable to map Apex runtime context: {e}")
    sys.exit(1)

def judge(claim_a: str, claim_b: str):
    """Wrapper for the DSPy Apex Judge to evaluate pairs directly."""
    logger.info("🧠 Apex Logic Engine evaluating pair...")
    return _apex_instance(claim_a=claim_a, claim_b=claim_b)