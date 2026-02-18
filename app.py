import os
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
from PyPDF2 import PdfReader
from ecfr_client import ECFRClient
from vector_store import initialize_rag
from graph import create_rip_graph

from langchain_ollama import OllamaLLM

# --- Setup ---
st.title("Clinical Audit & Regulatory Analysis (CLARA)")

#Initialize the Model (Local MedGemma via Ollama)
@st.cache_resource
def get_llm():
    # Make sure you have run: ollama run MedAIBase/MedGemma1.5:4b
    return OllamaLLM(
        model="MedGemma1.5:4b",
        temperature=0.1  # Keep it low for regulatory precision
    )
    
# Load multiple CFR parts for protocol audits (Part 11, human subjects, IND, cGMP, etc.)
_CFR_PART_FETCHERS = [
    ("21 CFR Part 11", ECFRClient.get_part_11_text),
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
law_text = "\n".join(law_text_parts) if law_text_parts else "No regulations loaded."
llm = get_llm()
retriever = initialize_rag(law_text)
graph = create_rip_graph(retriever, llm)

# --- UI ---
def extract_text(file):
    if file.type == "application/pdf":
        reader = PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    else:
        return file.read().decode("utf-8")

st.subheader("Upload Clinical Protocol")
uploaded_file = st.file_uploader("Choose a PDF or TXT file", type=["pdf", "txt"])
st.markdown("--- or ---")
pasted_text = st.text_area("Paste Protocol Section Here:", height=200)

final_protocol_text = ""
if uploaded_file is not None:
    final_protocol_text = extract_text(uploaded_file)
    st.success(f"File '{uploaded_file.name}' loaded successfully!")
elif pasted_text:
    final_protocol_text = pasted_text
    
if st.button("Run Regulatory Audit"):
    with st.spinner("MedGemma is cross-examining protocol..."):
        result = graph.invoke({"protocol_text": final_protocol_text})
        st.subheader("FDA Compliance Findings")
        st.markdown(result["audit_results"])
        
        with st.expander("View Retrieved Regulations"):
            for reg in result["retrieved_regulations"]:
                st.info(reg)