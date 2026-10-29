from typing import Any

import streamlit as st

from app.core.config import get_settings
from app.ui.api_client import APIClientError, DocumentAPIClient
from app.ui.components import (
    inject_styles,
    render_brand,
    render_citation_card,
    render_empty,
    render_metric,
    render_page_header,
    render_section_label,
    render_status,
    status_counts,
    toggle_selection,
)


PAGES = ("Overview", "Documents", "Research", "Reviews")
PAGE_ICONS = {"Overview": "⌂", "Documents": "▤", "Research": "⌕", "Reviews": "✓"}

st.set_page_config(page_title="DocuIntel AI", page_icon="DI", layout="wide", initial_sidebar_state="expanded")
inject_styles()


@st.cache_resource
def get_api_client(base_url: str, timeout: float) -> DocumentAPIClient:
    return DocumentAPIClient(base_url, timeout=timeout)


def load_documents(client: DocumentAPIClient) -> list[dict[str, Any]]:
    return client.list_documents(limit=100)


def navigate(page: str) -> None:
    st.session_state["active_page"] = page
    st.rerun()


def render_sidebar() -> str:
    active = st.session_state.get("active_page", "Overview")
    with st.sidebar:
        render_brand()
        st.markdown('<div class="di-caption">Your private evidence workspace</div>', unsafe_allow_html=True)
        st.markdown('<div class="di-nav-hint">Workspace navigation</div>', unsafe_allow_html=True)
        for page in PAGES:
            if st.button(f"{PAGE_ICONS[page]}  {page}", key=f"nav-{page}", type="primary" if page == active else "secondary", use_container_width=True):
                navigate(page)
        st.markdown('<div class="di-footer">Local-first processing<br>Human approval for workflow outputs</div>', unsafe_allow_html=True)
    return active


def render_step_navigation(page: str) -> None:
    current_index = PAGES.index(page)
    previous_page = PAGES[current_index - 1] if current_index > 0 else None
    next_page = PAGES[current_index + 1] if current_index < len(PAGES) - 1 else None
    st.markdown('<div class="di-step-nav"></div>', unsafe_allow_html=True)
    previous, next_column = st.columns(2)
    with previous:
        if previous_page and st.button(f"← Back to {previous_page}", key=f"step-back-{page}", use_container_width=True):
            navigate(previous_page)
    with next_column:
        if next_page:
            if st.button(f"Next: {next_page} →", key=f"step-next-{page}", type="primary", use_container_width=True):
                navigate(next_page)
        elif st.button("Return to overview →", key="step-next-reviews", type="primary", use_container_width=True):
            navigate("Overview")


def render_overview(client: DocumentAPIClient) -> None:
    render_page_header("Workspace overview", "Make every document answerable.", "A calm, local-first workspace for grounded research, traceable evidence, and human-reviewed workflow intelligence.")
    st.markdown('<div class="di-hero"><div class="di-kicker">A better starting point</div><div class="di-hero-copy">Bring source material into one focused workspace. DocuIntel extracts, indexes, and cites evidence without pretending uncertainty is certainty.</div></div>', unsafe_allow_html=True)
    primary, secondary = st.columns([1, 1])
    with primary:
        if st.button("Upload a document", type="primary", use_container_width=True):
            navigate("Documents")
    with secondary:
        if st.button("Open research workspace", use_container_width=True):
            navigate("Research")
    render_section_label("How to use DocuIntel")
    st.markdown(
        '<div class="di-guide"><div class="di-guide-grid">'
        '<div class="di-guide-step"><div class="di-guide-number">01</div><div class="di-guide-icon">＋</div><div><div class="di-guide-title">Add a source document</div><div class="di-guide-copy">Upload a PDF, DOCX, or TXT file from the Documents workspace.</div></div></div>'
        '<div class="di-guide-step"><div class="di-guide-number">02</div><div class="di-guide-icon">◈</div><div><div class="di-guide-title">Confirm it is indexed</div><div class="di-guide-copy">Wait for the indexed status before using a document as evidence.</div></div></div>'
        '<div class="di-guide-step"><div class="di-guide-number">03</div><div class="di-guide-icon">⌕</div><div><div class="di-guide-title">Ask with evidence</div><div class="di-guide-copy">Select indexed sources and inspect the citations returned with every answer.</div></div></div>'
        '<div class="di-guide-step"><div class="di-guide-number">04</div><div class="di-guide-icon">✓</div><div><div class="di-guide-title">Review before approval</div><div class="di-guide-copy">Inspect the draft, edit permitted fields, then approve or reject it explicitly.</div></div></div>'
        '</div></div>', unsafe_allow_html=True,
    )
    try:
        documents = load_documents(client)
    except APIClientError as error:
        st.warning(str(error))
        render_empty("Backend connection required", "Start FastAPI, then refresh this page to load the live workspace.")
        return
    counts = status_counts(documents)
    render_section_label("Workspace pulse")
    cols = st.columns(4)
    metrics = [("Documents", str(len(documents)), "Live records"), ("Indexed", str(counts["indexed"]), "Ready for research"), ("Processing", str(counts["processing"]), "Synchronous requests"), ("Needs attention", str(counts["failed"]), "Failed processing")]
    for col, values in zip(cols, metrics):
        with col:
            render_metric(*values)
    render_section_label("Recent documents")
    if not documents:
        render_empty("Your evidence workspace is ready", "Upload a PDF, DOCX, or TXT file to begin.")
    else:
        for document in documents[:5]:
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.markdown(f'<div class="di-row-title">{document.get("filename", "Untitled")}</div><div class="di-row-meta">{document.get("content_type", "unknown")} · {document.get("size_bytes", 0):,} bytes</div>', unsafe_allow_html=True)
            with cols[1]:
                render_status(str(document.get("status", "unknown")))
            with cols[2]:
                if st.button("Open", key=f"overview-open-{document.get('id')}"):
                    st.session_state["selected_document"] = str(document.get("id"))
                    navigate("Documents")


def render_upload(client: DocumentAPIClient) -> None:
    render_section_label("Add source material")
    st.markdown('<div class="di-panel"><div class="di-row-title">Bring a document into the workspace</div><div class="di-row-meta">PDF, DOCX, and TXT are processed synchronously through the local API.</div></div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Choose a document", type=["pdf", "docx", "txt"], help="The API enforces its configured upload limit.")
    if uploaded is not None and st.button("Process document", type="primary"):
        with st.spinner("Uploading and indexing document…"):
            try:
                result = client.upload_document(filename=uploaded.name, content=uploaded.getvalue(), content_type=uploaded.type)
                st.success(f"{result['filename']} is {result['status']}.")
                st.session_state["documents_refresh"] = True
            except APIClientError as error:
                st.error(str(error))
    st.caption("The API reports the final synchronous status; the interface does not simulate background progress.")


def render_document_row(client: DocumentAPIClient, document: dict[str, Any]) -> None:
    document_id = str(document.get("id", ""))
    cols = st.columns([3, 1, 1, 1])
    with cols[0]:
        st.markdown(f'<div class="di-row-title">{document.get("filename", "Untitled")}</div><div class="di-row-meta">{document.get("content_type", "unknown")} · {document.get("size_bytes", 0):,} bytes</div>', unsafe_allow_html=True)
    with cols[1]:
        render_status(str(document.get("status", "unknown")))
    with cols[2]:
        st.caption(str(document.get("created_at", "—"))[:19].replace("T", " "))
    with cols[3]:
        with st.popover("Manage"):
            if st.button("View details", key=f"view-{document_id}"):
                st.session_state["selected_document"] = document_id
                st.rerun()
            confirm = st.checkbox("Confirm deletion", key=f"confirm-{document_id}")
            if st.button("Delete document", key=f"delete-{document_id}", disabled=not confirm):
                try:
                    client.delete_document(document_id)
                    st.success("Document deleted.")
                    st.rerun()
                except APIClientError as error:
                    st.error(str(error))


def render_selected_document(client: DocumentAPIClient, document_id: str) -> None:
    try:
        document = client.get_document(document_id)
    except APIClientError as error:
        st.warning(str(error))
        return
    render_section_label("Document details")
    st.markdown(f'<div class="di-panel"><div class="di-row-title">{document.get("filename", "Document")}</div><div class="di-row-meta">{document.get("content_type", "unknown")} · {document.get("size_bytes", 0):,} bytes</div></div>', unsafe_allow_html=True)
    render_status(str(document.get("status", "unknown")))
    st.caption(f"ID: {document.get('id')} · SHA-256: {document.get('checksum')}")
    if document.get("error_message"):
        st.error(str(document["error_message"]))


def render_documents(client: DocumentAPIClient) -> None:
    render_page_header("Document library", "Your source material.", "Upload, inspect, and manage the documents that ground every answer and review.")
    render_upload(client)
    if st.button("Refresh library") or st.session_state.pop("documents_refresh", False):
        st.rerun()
    try:
        documents = load_documents(client)
    except APIClientError as error:
        st.error(str(error))
        render_empty("Document library unavailable", "The API did not return a document list. Check the backend and try again.")
        return
    render_section_label("Library")
    query = st.text_input("Search library", placeholder="Search by filename", label_visibility="collapsed")
    filtered = [doc for doc in documents if not query.strip() or query.lower() in str(doc.get("filename", "")).lower()]
    if not filtered:
        render_empty("No matching documents", "Uploaded source material will appear here with its processing status and metadata.")
    else:
        for document in filtered:
            render_document_row(client, document)
    selected = st.session_state.get("selected_document")
    if selected:
        render_selected_document(client, selected)


def render_research(client: DocumentAPIClient) -> None:
    render_page_header("Research workspace", "Ask with evidence.", "Select indexed sources, ask a focused question, and inspect exactly which chunks support the answer.")
    try:
        documents = [doc for doc in load_documents(client) if doc.get("status") == "indexed"]
    except APIClientError as error:
        st.warning(str(error))
        render_empty("Research needs the API", "Start FastAPI to load indexed documents.")
        return
    if not documents:
        render_empty("No indexed sources", "Process at least one document before opening a research session.")
        return
    selected = st.session_state.setdefault("research_selected_ids", [])
    valid_ids = {str(doc["id"]) for doc in documents}
    selected[:] = [item for item in selected if item in valid_ids]
    render_section_label("Choose evidence")
    for document in documents:
        document_id = str(document["id"])
        is_selected = document_id in selected
        label = ("Selected · " if is_selected else "Select · ") + str(document.get("filename", "Untitled"))
        if st.button(label, key=f"research-doc-{document_id}", type="primary" if is_selected else "secondary", use_container_width=True):
            st.session_state["research_selected_ids"] = toggle_selection(selected, document_id)
            st.rerun()
    if selected:
        st.markdown("".join(f'<span class="di-chip">{next((d.get("filename", "Untitled") for d in documents if str(d["id"]) == item), item)}</span>' for item in selected), unsafe_allow_html=True)
    question = st.text_area("Question", placeholder="What would you like to find in the selected sources?", height=130)
    ask = st.button("Ask the local research model", type="primary", disabled=not selected or not question.strip())
    context = (question.strip(), tuple(selected))
    if ask:
        with st.spinner("Retrieving evidence and asking the local model…"):
            try:
                st.session_state["research_result"] = client.ask_question(question=question.strip(), document_ids=selected)
                st.session_state["research_context"] = context
            except APIClientError as error:
                st.error(str(error))
    result = st.session_state.get("research_result") if st.session_state.get("research_context") == context else None
    if result:
        render_section_label("Answer")
        if result.get("abstained"):
            st.markdown(f'<div class="di-callout">{result.get("answer") or "Evidence is insufficient to answer this question."}</div>', unsafe_allow_html=True)
        else:
            st.markdown(str(result.get("answer", "")))
        render_section_label("Evidence references")
        citations = result.get("citations", [])
        if citations:
            for citation in citations:
                render_citation_card(citation)
        else:
            st.caption("No supporting citations were returned.")
    else:
        st.info("Answers are generated only from retrieved evidence and validated citations.")


def render_reviews(client: DocumentAPIClient) -> None:
    render_page_header("Workflow review", "Review before approval.", "Inspect evidence-backed structured output, edit permitted fields, and make an explicit human decision.")
    try:
        documents = [doc for doc in load_documents(client) if doc.get("status") == "indexed"]
    except APIClientError as error:
        st.warning(str(error))
        render_empty("Review needs the API", "Start FastAPI to load indexed documents.")
        return
    if not documents:
        render_empty("No indexed sources", "Process at least one document before creating a review.")
        return
    selected_document = st.session_state.get("review_document_id")
    valid_ids = {str(doc["id"]) for doc in documents}
    if selected_document not in valid_ids:
        selected_document = str(documents[0]["id"])
        st.session_state["review_document_id"] = selected_document
    render_section_label("Source document")
    for document in documents:
        document_id = str(document["id"])
        if st.button(("Selected · " if document_id == selected_document else "Select · ") + str(document.get("filename", "Untitled")), key=f"review-doc-{document_id}", type="primary" if document_id == selected_document else "secondary", use_container_width=True):
            st.session_state["review_document_id"] = document_id
            st.rerun()
    if st.button("Generate summary review", type="primary"):
        with st.spinner("Retrieving evidence and preparing a review…"):
            try:
                review = client.create_review(document_id=selected_document)
                st.session_state["selected_review"] = review["id"]
                st.success("Draft review created. Inspect it before deciding.")
            except APIClientError as error:
                st.error(str(error))
    try:
        reviews = client.list_reviews(document_id=selected_document)
    except APIClientError as error:
        st.error(str(error))
        return
    if not reviews:
        render_empty("No review drafts", "Generate a summary to create a human-reviewable draft.")
        return
    review_ids = {str(review["id"]): review for review in reviews}
    review_id = str(st.session_state.get("selected_review", next(iter(review_ids))))
    if review_id not in review_ids:
        review_id = next(iter(review_ids))
    st.session_state["selected_review"] = review_id
    render_section_label("Review drafts")
    for candidate_id, candidate in review_ids.items():
        label = ("Selected · " if candidate_id == review_id else "Open · ") + f'{candidate.get("status", "unknown")} · {str(candidate.get("created_at", ""))[:19]}'
        if st.button(label, key=f"review-{candidate_id}", type="primary" if candidate_id == review_id else "secondary", use_container_width=True):
            st.session_state["selected_review"] = candidate_id
            st.rerun()
    review = review_ids[review_id]
    result = review.get("structured_result") or {}
    render_section_label("Draft result")
    render_status(str(review.get("status", "unknown")))
    st.caption(f"Source: {next((d.get('filename') for d in documents if str(d['id']) == str(review.get('document_id'))), 'Unknown document')} · Type: {review.get('workflow_type', 'unknown')}")
    if review.get("error_message"):
        st.error(str(review["error_message"]))
    summary = st.text_area("Summary", value=str(result.get("summary", "")), height=180, disabled=review.get("status") != "pending_review")
    key_points = result.get("key_points") or []
    if key_points:
        st.markdown("**Key points**")
        for point in key_points:
            st.markdown(f"- {point}")
    render_section_label("Evidence references")
    for citation in result.get("citations", []):
        render_citation_card(citation)
    if review.get("status") == "pending_review":
        reviewer_note = st.text_area("Reviewer note", key=f"note-{review_id}", height=90)
        confirm = st.checkbox("I reviewed the evidence and this decision", key=f"confirm-{review_id}")
        approve, reject = st.columns(2)
        with approve:
            if st.button("Approve review", type="primary", disabled=not confirm, key=f"approve-{review_id}"):
                try:
                    client.approve_review(review_id, reviewer_note=reviewer_note or None, edited_summary=summary)
                    st.success("Review approved.")
                    st.rerun()
                except APIClientError as error:
                    st.error(str(error))
        with reject:
            if st.button("Reject review", disabled=not confirm, key=f"reject-{review_id}"):
                try:
                    client.reject_review(review_id, reviewer_note=reviewer_note or None)
                    st.warning("Review rejected.")
                    st.rerun()
                except APIClientError as error:
                    st.error(str(error))


def main() -> None:
    settings = get_settings()
    page = render_sidebar()
    client = get_api_client(settings.api_base_url, settings.api_timeout_seconds)
    if page == "Overview":
        render_overview(client)
    elif page == "Documents":
        render_documents(client)
    elif page == "Reviews":
        render_reviews(client)
    else:
        render_research(client)
    render_step_navigation(page)
    st.markdown('<div class="di-footer">DocuIntel AI · Local inference · Evidence before action</div>', unsafe_allow_html=True)


main()
