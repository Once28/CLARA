import re
from prompts import AUDIT_PROMPT

def retrieval_node(state, retriever):
    """Searches the law for sections relevant to the protocol text."""
    docs = retriever.invoke(state["protocol_text"])
    return {"retrieved_regulations": [d.page_content for d in docs]}

def audit_node(state, llm):
    """Uses MedGemma to perform audit and parses response into variables."""
    context = "\n\n".join(state["retrieved_regulations"])
    formatted_prompt = AUDIT_PROMPT.format(context=context, protocol=state["protocol_text"])
    
    response = llm.invoke(formatted_prompt)

    # --- Parsing Logic ---
    
    # 1. Extract Score: looks for FINAL_SCORE: [85]
    score_match = re.search(r"FINAL_SCORE:\s*\[(\d+)\]", response)
    score = int(score_match.group(1)) if score_match else 0
    
    # 2. Extract Status: looks for [APPROVED], [REJECTED], etc.
    status_match = re.search(r"Overall Status:\s*\[(.*?)\]", response)
    status = status_match.group(1) if status_match else "UNKNOWN"
    
    # 3. Extract Phase: looks for Phase: (I, II, etc.)
    phase_match = re.search(r"Phase:\s*(Phase\s*[0-IV]+|I|II|III|IV|0)", response, re.IGNORECASE)
    phase = phase_match.group(1) if phase_match else "Not Detected"

    # Return updated state with new variables
    return {
        "audit_results": response,
        "compliance_score": score,
        "approval_status": status,
        "study_phase": phase
    }