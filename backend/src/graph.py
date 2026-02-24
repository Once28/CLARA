from langgraph.graph import StateGraph, END
from state import AgentState
from nodes import retrieval_node, audit_node
from functools import partial

def create_rip_graph(retriever, llm):
    workflow = StateGraph(AgentState)
    
    # Add nodes with bound tools
    workflow.add_node("retrieve", partial(retrieval_node, retriever=retriever))
    workflow.add_node("audit", partial(audit_node, llm=llm))
    
    # Set edges: Start -> Retrieve -> Audit -> End
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "audit")
    workflow.add_edge("audit", END)
    
    return workflow.compile()