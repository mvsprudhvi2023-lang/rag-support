import os
import re

CHUNKS = []

def get_client():
    try:
        import streamlit as st
        key = st.secrets["GROQ_API_KEY"]
    except Exception:
        key = "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"
    
    from groq import Groq
    return Groq(api_key=key)

def load_pdf(filepath):
    try:
        import PyPDF2
        text = ""
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        chunks = split_into_chunks(text, source=os.path.basename(filepath))
        CHUNKS.extend(chunks)
        print(f"✅ Loaded '{os.path.basename(filepath)}' → {len(chunks)} chunks")
        return len(chunks)
    except Exception as e:
        print(f"❌ Error loading PDF: {e}")
        return 0

def load_text(text, source="manual_input"):
    chunks = split_into_chunks(text, source=source)
    CHUNKS.extend(chunks)
    print(f"✅ Loaded '{source}' → {len(chunks)} chunks")
    return len(chunks)

def split_into_chunks(text, source="unknown", chunk_size=400, overlap=80):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i : i + chunk_size]
        chunk_text = " ".join(chunk_words).strip()
        if len(chunk_text) > 60:
            chunks.append({"text": chunk_text, "source": source})
        i += chunk_size - overlap
    return chunks

def retrieve(query, top_k=5):
    if not CHUNKS:
        return []
    query_words = set(re.findall(r'\w+', query.lower()))
    scored = []
    for chunk in CHUNKS:
        chunk_words = set(re.findall(r'\w+', chunk["text"].lower()))
        overlap = len(query_words & chunk_words)
        scored.append((overlap, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k] if _ > 0]

def answer(question, language="English", history=None):
    relevant = retrieve(question)

    if not relevant:
        no_data = {
            "English": "I couldn't find relevant information in the uploaded documents.",
            "Spanish": "No encontré información relevante en los documentos cargados.",
            "French": "Je n'ai pas trouvé d'informations pertinentes dans les documents.",
            "German": "Ich konnte keine relevanten Informationen in den Dokumenten finden.",
            "Japanese": "アップロードされた文書に関連情報が見つかりませんでした。",
            "Arabic": "لم أجد معلومات ذات صلة في المستندات المحملة.",
        }
        return no_data.get(language, no_data["English"]), []

    context = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in relevant
    )
    sources = list({c["source"] for c in relevant})

    lang_instruction = {
        "English": "Respond in English.",
        "Spanish": "Responde completamente en español.",
        "French": "Réponds entièrement en français.",
        "German": "Antworte vollständig auf Deutsch.",
        "Japanese": "完全に日本語で回答してください。",
        "Arabic": "أجب بالكامل باللغة العربية.",
    }.get(language, "Respond in English.")

    system = f"""You are a helpful multilingual customer support assistant.
Answer the user's question using ONLY the context provided below.
If the answer isn't in the context, say so clearly.
Always be concise, friendly, and accurate.
{lang_instruction}

CONTEXT FROM DOCUMENTS:
{context}"""

    messages = [{"role": "system", "content": system}]
    for m in (history or []):
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": question})

    client = get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        messages=messages,
    )
    return response.choices[0].message.content, sources


if __name__ == "__main__":
    print("=== RAG self-test ===\n")
    load_text(
        """Return Policy: Customers may return unused items within 30 days for a full refund.
        Items must be in original packaging. Digital products are non-refundable.
        Contact support@company.com with your order number to start a return.
        Refunds are processed within 5-7 business days.""",
        source="return_policy.txt"
    )
    load_text(
        """Shipping FAQ: Standard shipping takes 5-7 business days.
        Express shipping (2-3 days) costs $9.99 extra.
        Free shipping on orders over $50. We ship to 40+ countries.
        Tracking numbers are emailed within 24 hours of dispatch.""",
        source="shipping_faq.txt"
    )
    q = "How long does shipping take?"
    ans, srcs = answer(q, language="English")
    print(f"Q: {q}")
    print(f"A: {ans}")
    print(f"Sources: {srcs}\n")

    q2 = "¿Cuánto tarda el envío?"
    ans2, srcs2 = answer(q2, language="Spanish")
    print(f"Q: {q2}")
    print(f"A: {ans2}")
    print(f"Sources: {srcs2}")
