# scripts/compile_apex.py
import os
import dspy
import random
from dspy.teleprompt import BootstrapFewShot
from dotenv import load_dotenv
from src.services.apex import Apex
from dataset.orqestra_50 import train_set

random.seed(42)
random.shuffle(train_set)

load_dotenv()

# ==========================================
# 1. INITIALIZE GPT-4o-MINI
# ==========================================
openai_key = os.environ.get("OPENAI_API_KEY")
nvidia_nim_key = os.environ.get("NVIDIA_NIM_API_KEY")

if not openai_key:
    raise ValueError("OPENAI_API_KEY not found in .env")

if not nvidia_nim_key:
    raise ValueError("OPENAI_API_KEY not found in .env")

# Direct OpenAI protocol for gpt-4o-mini
gpt_4o_mini = dspy.LM(
    model='openai/gpt-4o-mini', 
    api_key=openai_key,
    max_tokens=400
)

glm5_1 = dspy.LM(
    model='z-ai/glm-5.1', 
    api_key=nvidia_nim_key,
    api_base="https://integrate.api.nvidia.com/v1",
    max_tokens=500
)

#dspy.settings.configure(cache=False)
dspy.configure(lm=gpt_4o_mini)

# ==========================================
# 2. DEFINE THE VALIDATION METRIC
# ==========================================
def validate_nli_logic(example, prediction, trace=None):
    """
    The metric checks if the predicted relationship matches our gold standard,
    ignoring case sensitivity or accidental whitespace noise.
    """
    target = example.logical_relationship.strip().lower()
    predicted = prediction.logical_relationship.strip().lower()
    return target == predicted

# ==========================================
# 3. COMPILE THE APEX ENGINE
# ==========================================
if __name__ == "__main__":
    print("🧠 Starting Path A: Compiling Apex Logic Engine with GPT-4o-mini...")
    
    # Initialize our uncompiled Apex module
    uncompiled_apex = Apex()
    
    # Configure the Bootstrap teleprompter
    teleprompter = BootstrapFewShot(
        metric=validate_nli_logic,
        max_bootstrapped_demos=5,  # Finds the best 3 working context examples
        max_labeled_demos=5
    )
    
    # Compile! This runs gpt-4o-mini against the dataset to map logical behaviors
    compiled_apex = teleprompter.compile(
        student=uncompiled_apex,
        trainset=train_set
    )
    
    print("\n✅ Compilation Complete! Hardening prompt signatures...")
    
    # Save the compiled parameters so Path B can load it instantly for $0
    os.makedirs("models/apex_compiled", exist_ok=True)
    compiled_apex.save("models/apex_compiled/optimized_config.json")
    print("💾 Compiled configuration saved to 'models/apex_compiled/optimized_config.json'")

    #gpt_4o_mini.inspect_history(n=1)