import streamlit as st
import os
import tempfile
from rag import load_pdf, load_text, answer, CHUNKS

st.set_page_config(
    page_title="Multilingual Support Assistant",
    page_icon="🌍",
    layout="wide",
)

st.markdown("""
<style>
.stApp { max-width: 900px; margin: 0 auto; }
.source-badge {
    display: inline-block;
    background: #f0f2f6;
    color: #555;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    margin: 2px 3px;
}
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "loaded_docs" not in st.session_state:
    st.session_state.loaded_docs = []
if "docs_loaded_into_rag" not in st.session_state:
    st.session_state.docs_loaded_into_rag = False

with st.sidebar:
    st.markdown("## 🌍 Support Assistant")
    st.markdown("Upload your support docs and ask questions in **any language**.")
    st.divider()

    language = st.selectbox(
        "🗣️ Respond in",
        ["English", "Spanish", "French", "German", "Japanese", "Arabic"],
        index=0,
    )

    st.divider()
    st.markdown("### 📂 Upload Documents")
    uploaded_files = st.file_uploader(
        "Drop PDF files here",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for uf in uploaded_files:
            if uf.name not in st.session_state.loaded_docs:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uf.read())
                    tmp_path = tmp.name
                n = load_pdf(tmp_path)
                os.unlink(tmp_path)
                if n > 0:
                    st.session_state.loaded_docs.append(uf.name)
                    st.success(f"✅ {uf.name} loaded ({n} chunks)")

    if not st.session_state.loaded_docs and not st.session_state.docs_loaded_into_rag:
        load_text(
            """Return Policy: Customers may return unused items within 30 days of purchase for a full refund.
            Items must be in original packaging. Digital products and gift cards are non-refundable.
            To start a return, email support@company.com with your order number.
            Refunds are processed within 5-7 business days back to the original payment method.""",
            source="Return Policy"
        )
        load_text(
            """Shipping FAQ: Standard shipping takes 5-7 business days and is free on orders over $50.
            Express shipping (2-3 business days) costs $9.99. Overnight shipping costs $24.99.
            We ship to over 40 countries. International orders may have customs duties.
            Tracking numbers are emailed within 24 hours of dispatch.""",
            source="Shipping FAQ"
        )
        load_text(
            """Account Help: Reset your password using the Forgot Password link on the login page.
            For two-factor authentication issues, use your backup codes.
            To delete your account, go to Settings > Privacy > Delete Account.
            Account deletion is processed in 14 days and data is kept 90 days after.""",
            source="Account Help"
        )
        load_text(
            """Warranty: All products have a 12-month manufacturer warranty covering defects.
            Warranty does not cover accidental damage, water damage, or normal wear.
            To claim warranty, submit a ticket at support.company.com with proof of purchase.
            We will repair or replace defective products at our discretion.""",
            source="Warranty"
        )
        load_text(
            """Payment & Security: We accept Visa, Mastercard, Amex, PayPal, and Apple Pay.
            All payments are encrypted with TLS. We never store full card numbers.
            For billing disputes, contact billing@company.com within 60 days of the charge.
            Refunds appear on your statement within 5-10 business days.""",
            source="Payment & Security"
        )
        st.session_state.loaded_docs = ["Demo docs (5 topics)"]
        st.session_state.docs_loaded_into_rag = True

    st.divider()
    st.markdown("### 📊 Knowledge base")
    col1, col2 = st.columns(2)
    col1.metric("Docs", len(st.session_state.loaded_docs))
    col2.metric("Chunks", len(CHUNKS))

    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()

st.markdown("## 💬 Ask a question")
st.caption("Type in any language — the assistant replies in your chosen language.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            src_html = " ".join(
                f'<span class="source-badge">📄 {s}</span>'
                for s in msg["sources"]
            )
            st.markdown(src_html, unsafe_allow_html=True)

if prompt := st.chat_input("Ask anything about returns, shipping, accounts..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    history = []
    for m in st.session_state.messages[-12:]:
        history.append({"role": m["role"], "content": m["content"]})

    with st.chat_message("assistant"):
        with st.spinner("Searching docs and generating answer..."):
            reply, sources = answer(prompt, language=language, history=history[:-1])
        st.markdown(reply)
        if sources:
            src_html = " ".join(
                f'<span class="source-badge">📄 {s}</span>'
                for s in sources
            )
            st.markdown(src_html, unsafe_allow_html=True)

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "sources": sources,
    })

if not st.session_state.messages:
    st.markdown("---")
    st.markdown("### 💡 Try these examples")
    examples = [
        ("🇺🇸", "How do I return a product?"),
        ("🇪🇸", "¿Cuánto tarda el envío?"),
        ("🇫🇷", "Comment réinitialiser mon mot de passe?"),
        ("🇩🇪", "Was deckt die Garantie ab?"),
        ("🇯🇵", "返金はいつ受け取れますか？"),
        ("🇸🇦", "كيف يمكنني إلغاء طلبي؟"),
    ]
    cols = st.columns(3)
    for i, (flag, q) in enumerate(examples):
        with cols[i % 3]:
            if st.button(f"{flag} {q}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": q})
                reply, sources = answer(q, language=language)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply,
                    "sources": sources,
                })
                st.rerun()
