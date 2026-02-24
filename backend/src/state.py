from typing import TypedDict, List

class AgentState(TypedDict):
    protocol_text: str           # Raw text from the uploaded protocol
    retrieved_regulations: List[str]  # Relevant 21/45 CFR sections found in RAG
    audit_results: str           # The final analysis from MedGemma
    compliance_score: int        # A numeric 1-100 score
    approval_status: str     # Whether if protocol is approved
    study_phase: str    # Indicate phase of study