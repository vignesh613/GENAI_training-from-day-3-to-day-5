import uuid
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from db.chroma_client import store_document, query_documents
from utils.logger import get_logger

logger = get_logger(__name__)

_llm = None
_embeddings = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    return _llm


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return _embeddings


async def researcher_node(state: dict) -> dict:
    topic = state["topic"]
    logger.info(f"[RESEARCHER] Starting research on: {topic}")

    embeddings = get_embeddings()
    llm = get_llm()

    # Embed topic and retrieve any prior research from ChromaDB (RAG)
    topic_embedding = embeddings.embed_query(topic)
    retrieved_docs = query_documents(topic_embedding, n_results=3)
    retrieved_context = "\n\n---\n\n".join(retrieved_docs) if retrieved_docs else ""

    context_block = (
        f"\n\nRelevant prior knowledge from knowledge base:\n{retrieved_context}"
        if retrieved_context
        else ""
    )

    prompt = f"""You are a thorough research analyst. Conduct comprehensive research on the given topic.

Topic: {topic}{context_block}

Provide detailed, structured research notes covering:
1. **Overview & Definition** — Core concepts, scope, and significance
2. **Historical Background** — Origin, evolution, and key milestones
3. **Current State** — Latest developments, trends, and statistics
4. **Key Players & Stakeholders** — Organizations, experts, or entities involved
5. **Technical / Methodological Details** — How it works, key mechanisms
6. **Challenges & Controversies** — Known issues, debates, and limitations
7. **Opportunities & Applications** — Use cases and potential benefits
8. **Future Outlook** — Predictions, research directions, emerging trends

Be factual, comprehensive, and specific. Include concrete data points and examples."""

    response = llm.invoke(prompt)
    research_notes = response.content

    # Store research in ChromaDB for future retrieval
    doc_id = str(uuid.uuid4())
    research_embedding = embeddings.embed_query(research_notes[:2000])
    store_document(
        doc_id=doc_id,
        content=research_notes,
        metadata={"topic": topic, "type": "research_notes"},
        embedding=research_embedding,
    )

    logger.info(f"[RESEARCHER] Done — {len(research_notes)} chars")

    return {
        **state,
        "research_notes": research_notes,
        "retrieved_context": retrieved_context,
        "status": "researched",
    }
