import os
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
from ecfr_client import ECFRClient
from vector_store import initialize_rag
from graph import create_rip_graph
from langchain_google_vertexai import VertexAI # Or Ollama/HuggingFace
from langchain_google_genai import ChatGoogleGenerativeAI

# --- Setup ---
st.title("RIP: Regulatory Intelligence Platform")

# Load multiple CFR parts for protocol audits (Part 11, human subjects, IND, cGMP, etc.)
_CFR_PART_FETCHERS = [
    ("21 CFR Part 11", ECFRClient.get_part_11_text),
    ("21 CFR Part 46", ECFRClient.get_part_46_text),
    ("21 CFR Part 50", ECFRClient.get_part_50_text),
    ("21 CFR Part 56", ECFRClient.get_part_56_text),
    ("21 CFR Part 58", ECFRClient.get_part_58_text),
    ("21 CFR Part 211", ECFRClient.get_part_211_text),
    ("21 CFR Part 312", ECFRClient.get_part_312_text),
    ("21 CFR Part 314", ECFRClient.get_part_314_text),
    ("45 CFR Part 46", ECFRClient.get_part_45_46_text),
]
law_text_parts = []
for label, fetcher in _CFR_PART_FETCHERS:
    try:
        xml = fetcher()
        law_text_parts.append(f"\n\n<!-- {label} -->\n{xml}")
    except Exception as e:
        st.warning(f"Could not load {label}: {e}")
law_text = "\n".join(law_text_parts) if law_text_parts else ECFRClient.get_part_11_text()
retriever = initialize_rag(law_text)
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash") # Setup MedGemma endpoint

graph = create_rip_graph(retriever, llm)

# --- UI ---
protocol_input = st.text_area("Paste Protocol Section Here:", height=200)

if st.button("Run Regulatory Audit"):
    with st.spinner("MedGemma is cross-examining protocol..."):
        result = graph.invoke({"protocol_text": protocol_input})
        st.subheader("FDA Compliance Findings")
        st.markdown(result["audit_results"])
        
        with st.expander("View Retrieved Regulations"):
            for reg in result["retrieved_regulations"]:
                st.info(reg)