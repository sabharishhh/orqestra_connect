import os
import dspy

from dotenv import load_dotenv
load_dotenv()

# ==========================================
# 1. CONFIGURE THE LLM PROVIDER
# ==========================================
# For the Supreme Court, we need a high-reasoning model. 
openai_api_key = os.environ.get("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in .env")

# Note: Added 'openai/' prefix which DSPy 2.x+ prefers for clarity
llm = dspy.LM(
    model='openai/gpt-4o-mini', 
    api_key=openai_api_key,
    max_tokens=500
)

dspy.configure(lm=llm)

# ==========================================
# 2. THE SIGNATURE (The Rules of Logic)
# ==========================================
class EnterpriseContradictionJudge(dspy.Signature):
    """
    Evaluate two claims from different enterprise systems. 
    Strip away the domain vocabulary and extract the raw entities, conditions, and actions.
    Determine if the two actions can logically co-exist under the exact same conditions.
    """
    
    # Inputs
    claim_a = dspy.InputField(desc="The policy or rule stated by System A")
    claim_b = dspy.InputField(desc="The policy or rule stated by System B")
    
    # Forced Reasoning Steps (Chain of Thought)
    extracted_entities = dspy.OutputField(desc="What is the core subject? (e.g., Metformin, PTO, Server Access)")
    extracted_conditions = dspy.OutputField(desc="Under what specific conditions do these rules apply? (e.g., eGFR < 30, Friday afternoons)")
    extracted_actions = dspy.OutputField(desc="What actions are mandated or forbidden by each claim?")
    
    # Final Output
    logical_relationship = dspy.OutputField(desc="Must be exactly one of: 'Contradiction', 'Entailment', or 'Neutral'.")
    reasoning = dspy.OutputField(desc="A one-sentence explanation of the logical proof.")

# ==========================================
# 3. THE MODULE (The Execution Engine)
# ==========================================
class Apex(dspy.Module):
    # FIX: Added compiled_path parameter here!
    def __init__(self, compiled_path=None):
        super().__init__()
        self.evaluate_logic = dspy.ChainOfThought(EnterpriseContradictionJudge)
        
        # FIX: Tell the engine to actually load the JSON file if it is passed in!
        if compiled_path and os.path.exists(compiled_path):
            self.load(compiled_path)
        elif compiled_path:
            print(f"⚠️ Warning: Compiled brain not found at {compiled_path}. Running uncompiled.")

    def forward(self, claim_a: str, claim_b: str):
        # Pass the claims into the predictor
        result = self.evaluate_logic(claim_a=claim_a, claim_b=claim_b)
        return result