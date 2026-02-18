### Project Name

**Regulatory-Intelligence-Platform (RIP):** A multi-modal agentic platform to automate the "Regulatory Cross-Examination" of clinical trial protocols, ensuring alignment with federal regulations and global ethical standards.

### Team

**Justin Zeng** (Columbia University '26, University of Washington '24) — Academic experience in bioinformatics and data science; currently a researcher at Columbia's Irving Medical Center. Justin identified the core medical components and built the agentic workflow process to emulate clinical trial protocol review processes.

**Kennard Mah** (Columbia University '25, Imperial College London '24) — Academic experience in human-centered design engineering and data science. Kennard aligned the workflow with human-centered design principles, bridging the technical architecture with practical clinical applications.

Both Justin and Kennard contributed to the codebase, UI/UX design, and research into current clinical processes to identify high-impact areas for AI integration.

### Problem Statement

#### Problem Domain

Every clinical trial must undergo regulatory cross-examination — a labor-intensive process where protocol documents are scrutinized against federal regulations (e.g., 21 CFR Parts 50, 56, 312, and 812), ICH-GCP guidelines (E6(R2)), and institutional ethical standards. This process is the critical bottleneck in the clinical trial pipeline:

1. **Manual and repetitive:** Regulatory specialists must cross-reference dense protocol language against hundreds of pages of federal regulation, a process that is error-prone and requires lots of time.
2. **Subject matter specialization:** The task demands deep domain expertise in both clinical medicine and regulatory law, a very specialized combination of skills.
3. **High-impact:** A single oversight — a missing informed consent clause, an inadequate adverse event reporting plan, or a non-compliant inclusion/exclusion criterion — can result in FDA clinical holds, IRB rejections, or costly protocol amendments that delay trials by months.

At the core of AI and data science, we believe the highest impact lies in solving repetitive tasks that require specialized skills — tackling the "unsexy" bottleneck work that distracts researchers from scientific innovation. In clinical trials, regulatory cross-examination is precisely that bottleneck.

#### Impact Potential

There is strong impact potential in terms of automating clinical trial proocol reviews:

- **Over 300,000 clinical trials** are registered globally at any given time (ClinicalTrials.gov), each requiring regulatory review.
- The average Phase III trial costs **$11.5M–$52.9M**, with regulatory delays adding an estimated **$37,000 per day** in opportunity costs (Tufts CSDD).
- **~80% of clinical trials** experience delays, with regulatory and IRB review being a leading contributor.
- Protocol amendments, often triggered by regulatory non-compliance discovered late, occur in **57% of trials** and cost an average of **$535,000 per amendment** (Tufts CSDD).

By automating regulatory cross-examination, RIP can significantly reduce review cycle times from weeks to minutes, catch compliance gaps before submission, and free clinical practicians to focus on research rather than line-by-line cross-referencing.

### Overall Solution

RIP employs a Retrieval-Augmented Generation (RAG) pipeline with an agentic multi-step workflow that mirrors how a human regulatory specialist reviews a clinical trial protocol.

In terms of effectively using HAI-DEF models, since clinical trial protocols use highly specialized language — phrases like *"serious adverse event reporting within 24 hours"*, *"informed consent per 21 CFR 50.25"*, or *"IND safety reports per 312.32"* — that carry precise regulatory meaning. Rather than fine-tuning a model (which risks hallucination on regulatory citations), we built a RAG pipeline that grounds every assessment in retrieved regulatory text, ensuring traceability and auditability — a non-negotiable requirement in regulated industries. We leveraged HAI-DEF's embedding model for our vector store to capture medical languages effectively, in terms of domain-sensitive embeddings, higher retrieval precision, and generative cross-examination.

1. **Domain-sensitive embeddings:** Compared to general-purpose embedding models, HAI-DEF's model captures the semantic nuances of medical and regulatory language — distinguishing, for example, between *"adverse event"* (clinical) and *"adverse action"* (legal) — which is critical for accurate retrieval in our RAG pipeline.
2. **Retrieval precision:** Our ChromaDB vector store indexes chunked regulatory documents (CFR titles, ICH guidelines, FDA guidance documents) using HAI-DEF embeddings, enabling high-precision semantic search when the agentic system queries specific regulatory requirements.
3. **Generative cross-examination:** HAI-DEF's generative model powers the final compliance assessment, synthesizing retrieved regulatory passages with protocol content to produce structured, citation-backed compliance reports.

The platform implements a multi-agent architecture using LangGraph, orchestrating specialized agents in a directed workflow:

```
Protocol Upload → Document Parsing → Section Extraction →
  ┌─────────────────────────────────────────────────────────┐
  │  Agent 1: Regulatory Retrieval Agent                    │
  │  (Queries ChromaDB for relevant CFR/ICH sections)       │
  ├─────────────────────────────────────────────────────────┤
  │  Agent 2: Compliance Assessment Agent                   │
  │  (Cross-examines protocol sections against regulations) │
  ├─────────────────────────────────────────────────────────┤
  │  Agent 3: Gap Analysis Agent                            │
  │  (Identifies missing elements and non-compliance risks) │
  ├─────────────────────────────────────────────────────────┤
  │  Agent 4: Recommendation Agent                          │
  │  (Generates actionable remediation suggestions)         │
  └─────────────────────────────────────────────────────────┘
→ Structured Compliance Report with Citations
```

Each agent operates with a defined scope and passes structured state to the next, ensuring deterministic, auditable reasoning chains rather than a single monolithic LLM call.

### Technical Details

The technical details will cover the technology stack, product feasibility through understanding how users interact with RIP, and how the tool is evaluated to ensure continuous improvement and high-quality performance.

#### Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| **Frontend** | Streamlit | Interactive web interface for protocol upload and report viewing |
| **Orchestration** | LangGraph + LangChain | Multi-agent workflow with stateful graph execution |
| **Vector Store** | ChromaDB (persistent) | Stores embeddings of regulatory documents for semantic retrieval |
| **Embeddings** | HAI-DEF Embedding Model | Generates domain-aware vector representations of regulatory text |
| **LLM** | HAI-DEF Generative Model | Powers compliance reasoning and report generation |
| **Document Processing** | PyPDF / custom parsers | Extracts and chunks clinical trial protocols and regulatory PDFs |
| **Language** | Python 3.11+ | Core application logic |

#### How Do Users Interact with This Tool

1. **Upload:** A clinical researcher or regulatory specialist uploads their clinical trial protocol (PDF) through the Streamlit interface.
2. **Configure:** The user selects which regulatory frameworks to cross-examine against (e.g., FDA 21 CFR, ICH-GCP E6(R2), specific institutional requirements).
3. **Review:** The platform processes the document through its agentic pipeline and returns a structured compliance report with:
   - Section-by-section compliance status (Compliant / Non-Compliant / Needs Review)
   - Specific regulatory citations for each finding
   - Gap analysis identifying missing required elements
   - Actionable recommendations for remediation
4. **Iterate:** Researchers can modify their protocol and re-upload for continuous compliance checking, creating a tight feedback loop before formal IRB/FDA submission.

#### What This Tool Accomplishes

RIP serves as an AI-powered regulatory reviewer that:

- Reduces review time from days/weeks to minutes for initial compliance screening
- Democratizes regulatory expertise**by making federal regulation accessible to researchers without deep regulatory training
- Improves protocol quality through iterative, instant feedback before formal submission
- Maintains auditability by grounding every finding in specific, cited regulatory text — never hallucinated compliance claims

Acknowledging that a "positive" result means a protocol section is deemed compliant, we optimized for high precision score (i.e., minimizing cases where the system incorrectly marks a non-compliant section as compliant.) The downstream cost of a false positive (missed non-compliance reaching FDA/IRB review) far exceeds the cost of a false negative (flagging a compliant section for human review).

This asymmetric cost function informed our design decisions:

- Conservative retrieval: We retrieve a broader set of regulatory passages (higher recall) to reduce the chance of missing a relevant regulation.
- Structured output parsing: Agents output structured JSON assessments with explicit compliance rationale, enabling human reviewers to quickly verify flagged items.
- Human-in-the-loop feedback-driven design: The tool is designed as a decision-support system, not a decision-making system. While this tool will provide recommendations, the tracability ensures that final compliance determinations rest with qualified human reviewers.

#### Product Feasibility

The platform is fully functional as a prototype and designed for integration into existing clinical workflows. RIP allows researchers to continue writing protocols in their existing tools by accepting standard PDF uploads, requiring no changes to their current process. Researchers can iteratively improve protocols using RIP’s instant feedback, enabling a ‘write → check → revise’ loop that improves protocol quality before the formal and costly review process.

While the current version has been tested on a subset of regulations, the system is built on an immutable Directed Acyclic Graph (DAG) architecture, allowing new regulations, guidance documents, or institutional policies to be added to the ChromaDB vector store without retraining models. This modular structure ensures that individual components of the workflow can be updated independently and rolled back when necessary to isolate and analyze errors.

Additionally, the LangGraph agent framework enables extensibility through modular specialized agents, such as budget compliance or site feasibility agents, allowing new validation capabilities to be added without modifying the core system.

### References

- Tufts Center for the Study of Drug Development (CSDD). "Impact of Protocol Amendments on Clinical Trial Performance and Cost."
- U.S. Code of Federal Regulations, Title 21, Parts 50, 56, 312, 812.
- ICH Harmonised Guideline: Integrated Addendum to ICH E6(R1): Guideline for Good Clinical Practice E6(R2).
- ClinicalTrials.gov, U.S. National Library of Medicine.