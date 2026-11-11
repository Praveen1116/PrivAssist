import re
import chromadb
from pypdf import PdfReader

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "privacy_policy"

def load_and_index_policy(pdf_path: str = "data/Privacy.pdf") -> chromadb.Collection:
    """Reads Privacy.pdf, splits into legal sections, and indexes into ChromaDB."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    if collection.count() > 0:
        return collection

    reader = PdfReader(pdf_path)
    full_text = "\n".join(page.extract_text() for page in reader.pages)

    # Split into sections and subclauses
    raw_sections = re.split(r"\n(?=Section \d+:)", full_text)
    chunks, ids, metadatas = [], [], []

    for i, sec in enumerate(raw_sections):
        sec = sec.strip()
        if not sec:
            continue
        if "Section 7:" in sec:
            sub_chunks = re.split(r"\n(?=7\.\d+ )", sec)
            for j, sc in enumerate(sub_chunks):
                sc = sc.strip()
                if sc:
                    header = sc.split("\n")[0].strip()
                    chunks.append(sc)
                    ids.append(f"sec7_{j}")
                    metadatas.append({"header": header, "section": "Section 7"})
        else:
            header = sec.split("\n")[0].strip()
            chunks.append(sec)
            ids.append(f"sec_{i}")
            metadatas.append({"header": header, "section": f"Section {i}"})

    collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    return collection

def search_policy(query: str, n_results: int = 2) -> list[dict]:
    """Semantic retrieval of policy clauses relevant to a DSAR query."""
    collection = load_and_index_policy()
    results = collection.query(query_texts=[query], n_results=n_results)

    retrieved = []
    for doc, meta, doc_id in zip(results["documents"][0], results["metadatas"][0], results["ids"][0]):
        retrieved.append({
            "id": doc_id,
            "header": meta.get("header", ""),
            "text": doc
        })
    return retrieved

if __name__ == "__main__":
    print("Testing Policy RAG retrieval...")
    test_query = "What happens if the requester identity is unverified?"
    matches = search_policy(test_query, n_results=1)
    for m in matches:
        print(f"\n[MATCH] {m['header']}\n{m['text'][:250]}...\n")

