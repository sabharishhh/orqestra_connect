import os
import logging
from pydantic import BaseModel
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("HealthTrack.Extractor")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Define the exact JSON structure we want OpenAI to return
class ClinicalClaim(BaseModel):
    subject: str
    predicate: str
    object: str
    clinical_context: str

class ExtractionResponse(BaseModel):
    claims: List[ClinicalClaim]

def extract_claims(agent_output: str) -> List[dict]:
    """Uses an LLM to parse a paragraph of text into discrete SPO claims."""
    logger.info("Parsing raw output into discrete claims...")
    
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-5.4-mini",
            messages=[
                {"role": "system", "content": "You are a rigid clinical compliance parser. Extract ONLY actionable medical directives, medication rules, or procedural instructions. IGNORE patient history, lab values, or diagnostic statements. Format as strict Subject-Predicate-Object claims. Keep them atomic and one-sentence long."},
                {"role": "user", "content": f"Extract claims from this medical recommendation:\n\n{agent_output}"}
            ],
            response_format=ExtractionResponse,
            temperature=0.0
        )
        
        parsed_data = response.choices[0].message.parsed
        
        # Format them into readable single sentences
        formatted_claims = []
        for claim in parsed_data.claims:
            sentence = f"{claim.subject} {claim.predicate} {claim.object}. (Context: {claim.clinical_context})"
            formatted_claims.append(sentence)
            
        return formatted_claims
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return [agent_output] # Fallback to raw text if extraction fails