import os
import dspy
from dotenv import load_dotenv

# Load environment variables (API Keys)
load_dotenv()

# ==========================================
# 1. CONFIGURE THE LLM PROVIDER
# ==========================================
# For the Supreme Court, we need a high-reasoning model. 
# You can use gpt-4o, claude-3-5-sonnet, or a local Llama-3-70b.
openai_api_key = os.environ.get("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in .env")

llm = dspy.LM(
    model='gpt-4o-mini', # Fast, cheap, and highly logical for testing
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
    def __init__(self):
        super().__init__()
        # We wrap our signature in a ChainOfThought predictor.
        # This mathematically forces the LLM to fill out the extraction fields 
        # BEFORE it is allowed to guess the final logical relationship.
        self.evaluate_logic = dspy.ChainOfThought(EnterpriseContradictionJudge)

    def forward(self, claim_a: str, claim_b: str):
        # Pass the claims into the predictor
        result = self.evaluate_logic(claim_a=claim_a, claim_b=claim_b)
        
        # We can clean or format the output here if needed
        return result

# ==========================================
# 4. LIVE TEST (Run this file directly to test)
# ==========================================
if __name__ == "__main__":
    judge = Apex()

    print("🏛️  Orqestra Supreme Court Initialized...\n")
    
    # Test Case 1: The "Specific Exception" (Medical) - Should be NEUTRAL
    c_a = "Metformin is the standard first-line treatment for Type 2 diabetes."
    c_b = "Metformin must be discontinued if eGFR falls below 30."
    
    print(f"Claim A: {c_a}")
    print(f"Claim B: {c_b}")
    print("-" * 40)
    
    verdict = judge(claim_a=c_a, claim_b=c_b)
    
    print(f"Entities:   {verdict.extracted_entities}")
    print(f"Conditions: {verdict.extracted_conditions}")
    print(f"Actions:    {verdict.extracted_actions}")
    print(f"\nVERDICT:    {verdict.logical_relationship.upper()}")
    print(f"REASONING:  {verdict.reasoning}\n")