from prompts import AUDIT_PROMPT

def retrieval_node(state, retriever):
    """Searches the law for sections relevant to the protocol text."""
    docs = retriever.invoke(state["protocol_text"])
    return {"retrieved_regulations": [d.page_content for d in docs]}

def audit_node(state, llm):
    """Uses MedGemma to perform the actual cross-examination."""
    context = "\n\n".join(state["retrieved_regulations"])
    formatted_prompt = AUDIT_PROMPT.format(context=context, protocol=state["protocol_text"])
    
    # Simulate LLM call (Replace with medgemma.invoke)
    response = llm.invoke(formatted_prompt)
    return {"audit_results": response}