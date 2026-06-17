import sys
from pathlib import Path

# Fix path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.healthtrack.agents import guidelines_agent, med_review_agent

# The Trap: A patient with an eGFR exactly between the two conflicting rules.
PATIENT_PROFILE = """
Age: 68
Condition: Type 2 Diabetes
Current Meds: Metformin 1000mg BID
Recent Labs: eGFR is 38 mL/min (Declining from 50 six months ago).
"""

print("🏥 Welcome to HealthTrack Medical System\n")
print(f"Loading Patient Profile...\n{PATIENT_PROFILE}\n")

# Run Agent A
print(f"🤖 Querying {guidelines_agent.name}...")
output_a = guidelines_agent.analyze(PATIENT_PROFILE)
print(f"Result:\n{output_a}\n")

# Run Agent B
print(f"🤖 Querying {med_review_agent.name}...")
output_b = med_review_agent.analyze(PATIENT_PROFILE)
print(f"Result:\n{output_b}\n")

print("⚠️ Notice the conflict? One says stop, one says continue.")
print("This is exactly what Orqestra is built to catch in production.")