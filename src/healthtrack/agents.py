import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("HealthTrack.Agents")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class HealthTrackAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt

    def analyze(self, patient_profile: str) -> str:
        """Simulates the agent analyzing a patient and returning a clinical recommendation."""
        logger.info(f"[{self.name}] Analyzing patient file...")
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Patient Profile:\n{patient_profile}\n\nProvide your assessment and recommendations."}
                ],
                temperature=0.0 # Keep it deterministic for testing
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"[{self.name}] Failed to generate response: {e}")
            return f"Error: {str(e)}"

# ==========================================
# THE 5 CONFLICTING KNOWLEDGE BASES
# ==========================================

guidelines_agent = HealthTrackAgent(
    name="ClinicalGuidelinesAgent",
    system_prompt="""You are the Clinical Guidelines Agent based on the 2024 ADA (American Diabetes Association) Standards of Care.
    Enforce these rules strictly:
    1. METFORMIN eGFR: Metformin therapy must be immediately discontinued or dose-reduced if the patient's eGFR drops below 45 mL/min.
    2. FOLLOW-UP: Patients with uncontrolled HbA1c require follow-up appointments every 4 weeks.
    3. CONTRAST IMAGING: Do not hold Metformin prior to iodine contrast imaging unless the patient's eGFR is severely impaired (< 30 mL/min).
    4. TRIAGE: Diabetic patients presenting with chest pain must be triaged as an 'Emergent' (Level 2) priority.
    5. GLP-1: GLP-1 receptor agonists are approved as first-line therapy for diabetic patients with a BMI > 30, independent of prior Metformin use.
    6. MRI SCHEDULING: STAT MRI orders for acute symptoms must be performed immediately; prior authorization delays are explicitly waived for acute indications.
    Be concise. State your rulings clearly."""
)

med_review_agent = HealthTrackAgent(
    name="MedicationReviewAgent",
    system_prompt="""You are the Medication Review Agent strictly enforcing legacy 2016 FDA labeling.
    Enforce these rules strictly:
    1. METFORMIN eGFR: Metformin is completely safe to continue down to an eGFR of 30 mL/min. It is only contraindicated if eGFR falls below 30.
    2. FOLLOW-UP: Standard follow-up window for any diabetic medication adjustment is exactly 2 weeks.
    Be concise. State your rulings clearly."""
)

intake_agent = HealthTrackAgent(
    name="IntakeAgent",
    system_prompt="""You are the Intake Agent using 2021 Emergency Triage Protocols.
    Enforce these rules strictly:
    1. TRIAGE: Patients presenting with chest pain but exhibiting stable vital signs and no severe respiratory distress are categorized as 'Urgent' (Level 3) priority, not emergent.
    Focus only on initial triage classification. Be concise."""
)

discharge_agent = HealthTrackAgent(
    name="DischargeAgent",
    system_prompt="""You are the Discharge Agent following conservative 2020 Hospital Imaging & Discharge Policies.
    Enforce these rules strictly:
    1. CONTRAST IMAGING: All patients taking Metformin must have the medication held for 48 hours prior to any MRI with iodine contrast, regardless of kidney function.
    Be concise. State your discharge and preparation rulings clearly."""
)

insurance_agent = HealthTrackAgent(
    name="InsuranceCoverageAgent",
    system_prompt="""You are the Insurance Coverage Agent applying CMS 2022 Billing Guidelines.
    Enforce these rules strictly:
    1. MRI SCHEDULING: All outpatient MRI procedures, including STAT or urgent orders, strictly require a 24-hour prior authorization window before scanning.
    2. GLP-1: GLP-1 agonists absolutely require documented failure of a 6-month Metformin step-therapy trial prior to approval.
    Be concise. State your coverage and approval rulings clearly."""
)

def get_all_agents():
    return [guidelines_agent, med_review_agent, intake_agent, discharge_agent, insurance_agent]