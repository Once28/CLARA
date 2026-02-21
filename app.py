import os
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
from PyPDF2 import PdfReader
from ecfr_client import ECFRClient
from vector_store import index_protocol, query_protocol_for_regulation
from nodes import audit_node

from medgemma_llm import MedGemmaVertexLLM

# --- Setup ---
st.title("Clinical Audit & Regulatory Analysis (CLARA)")

# Initialize the Model (MedGemma via Google Cloud Vertex AI Endpoint)
@st.cache_resource
def get_llm():
    return MedGemmaVertexLLM(
        project=os.environ["GCP_PROJECT_ID"],
        location=os.environ.get("GCP_REGION", "europe-west4"),
        endpoint_id=os.environ["VERTEX_ENDPOINT_ID"],
        temperature=0.1,  # Keep it low for regulatory precision
        max_tokens=4096,
    )

# Load regulation texts (used to query protocol index per regulation)
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
regulation_texts = {}
for label, fetcher in _CFR_PART_FETCHERS:
    try:
        regulation_texts[label] = fetcher()
    except Exception as e:
        st.warning(f"Could not load {label}: {e}")

retriever = initialize_rag(law_text)
graph = create_rip_graph(retriever, llm)
llm = get_llm()

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
    if not final_protocol_text.strip():
        st.error("Please upload a file or paste protocol text.")
    elif not regulation_texts:
        st.error("No regulations loaded. Check eCFR connection.")
    else:
        with st.spinner("Chunking and indexing protocol, then checking each CFR regulation..."):
            # Index uploaded protocol (chunk + embed)
            protocol_vector_db = index_protocol(final_protocol_text)
            # For each regulation, query protocol to find addressing sections
            context_parts = []
            for label, reg_text in regulation_texts.items():
                chunks = query_protocol_for_regulation(protocol_vector_db, reg_text, k=5)
                reg_excerpt = (reg_text[:3500] + "...") if len(reg_text) > 3500 else reg_text
                protocol_excerpts = "\n\n".join(chunks) if chunks else "(No matching protocol sections found for this regulation.)"
                context_parts.append(
                    f"### {label}\n\n**Regulation (excerpt):**\n{reg_excerpt}\n\n**Protocol sections addressing this regulation:**\n{protocol_excerpts}"
                )
            context = "\n\n---\n\n".join(context_parts)
            state = {"protocol_text": final_protocol_text, "retrieved_regulations": [context]}
            result = audit_node(state, llm)

        # --- UI Dashboard ---
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Compliance Score", f"{result['compliance_score']}/100")

        with col2:
            color = "green" if result['approval_status'] == "APPROVED" else "orange"
            st.markdown(f"**Status:** :{color}[{result['approval_status']}]")

        with col3:
            st.write(f"**Detected Phase:** {result['study_phase']}")

        st.divider()

        # Show full report
        st.subheader("Detailed Auditor Report")
        st.markdown(result["audit_results"])
law_text = "\n".join(law_text_parts) if law_text_parts else "No regulations loaded."