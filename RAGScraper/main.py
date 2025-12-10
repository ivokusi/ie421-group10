from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
import os


# -----------------------------
# Setup
# -----------------------------
load_dotenv()

openai = OpenAI()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise RuntimeError("PINECONE_API_KEY not set in environment")

pc = Pinecone(api_key=PINECONE_API_KEY)

INDEX_NAME = "ie421-group10"
index = pc.Index(INDEX_NAME)


# -----------------------------
# Embedding helper
# -----------------------------
def embed_query(text: str):
    """Return OpenAI embedding vector for the input text."""
    resp = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return resp.data[0].embedding


# -----------------------------
# Stage 1: find parent objects
# -----------------------------
def find_parent_objects(
    query_text: str,
    top_k_parents: int = 5,
    namespace: str = "objects",
):
    """
    Search the 'objects' namespace for likely parent objects (classes/types)
    relevant to the user query.

    Expected metadata in 'objects' namespace (your case):
        - className: str (e.g. "APIPreferences", "CommandEventArgs")
        - text: str (documentation chunk)
    """
    vec = embed_query(query_text)

    res = index.query(
        vector=vec,
        top_k=top_k_parents,
        include_metadata=True,
        namespace=namespace,
    )

    matches = res.get("matches", [])

    # Debug: see what we got back
    print(f"\n[DEBUG] Stage 1 raw match count: {len(matches)}")
    for i, m in enumerate(matches[:3]):
        md = m.get("metadata", {}) or {}
        print(f"[DEBUG] Match {i} metadata keys: {list(md.keys())}")
    print("-" * 60)

    print(f"[Stage 1] Top {top_k_parents} parent objects (namespace='{namespace}'):")
    print("-" * 60)

    parents = []
    for m in matches:
        md = m.get("metadata", {}) or {}

        # In your schema, the parent name is stored under 'className'
        name = md.get("className")  # <-- key change here

        # If you later add more fields like 'kind', you can read them too
        kind = md.get("kind", "")
        score = m.get("score", 0.0)

        if not name:
            continue

        parents.append(
            {
                "name": name,
                "kind": kind,
                "score": score,
                "metadata": md,
            }
        )

        kind_str = f" [{kind}]" if kind else ""
        print(f"{name}{kind_str} (score={score:.3f})")

    if not parents:
        print("No parent objects found.")
    print("-" * 60)

    return parents


# -----------------------------
# Stage 2: query attributes for those parents
# -----------------------------
def query_attrs_for_parents(
    query_text: str,
    parent_names: list[str],
    namespace: str = "object_attrs",
    top_k_attrs: int = 8,
    top_k_raw: int = 50,
):
    """
    Given candidate parent object names, search 'object_attrs' namespace
    for the most relevant attributes/events/properties.

    Expected metadata in 'object_attrs' namespace:
        - className: str (e.g. "APIPreferences")
        - propertyName: str (e.g. "debuggingPort")
        - propertyType: str (e.g. "Event", "Property", "Method")
        - text: str  (documentation chunk)
    """
    if not parent_names:
        print("\n[Stage 2] No parents found. Cannot filter by className.")
        print("Falling back to global diverse attr search.\n")
        return query_pinecone_diverse(
            query_text=query_text,
            namespace=namespace,
            top_k=top_k_attrs,
            top_k_raw=top_k_raw,
        )

    vec = embed_query(query_text)

    # Filter attributes by candidate parent classes
    attr_filter = {
        "className": {"$in": parent_names}
    }

    res = index.query(
        vector=vec,
        top_k=top_k_raw,
        include_metadata=True,
        namespace=namespace,
        filter=attr_filter,
    )

    matches = res.get("matches", [])

    # Group by (className, propertyName) to get diversity
    grouped_best = {}  # key: (cls, prop) -> best match dict

    for m in matches:
        md = m.get("metadata", {}) or {}
        cls = md.get("className")
        prop = md.get("propertyName")

        key = (cls, prop)

        # Keep the highest-scoring chunk per (className, propertyName)
        if key not in grouped_best or m["score"] > grouped_best[key]["score"]:
            grouped_best[key] = m

    best_per_attr = list(grouped_best.values())
    best_per_attr.sort(key=lambda m: m["score"], reverse=True)
    final_matches = best_per_attr[:top_k_attrs]

    print(
        f"\n[Stage 2] Top {len(final_matches)} attributes for parents "
        f"{parent_names} (namespace='{namespace}'):"
    )
    print("-" * 60)

    for m in final_matches:
        md = m.get("metadata", {}) or {}
        score = m.get("score", 0.0)
        cls = md.get("className", "")
        prop = md.get("propertyName", "")
        ptype = md.get("propertyType", "")
        text = md.get("text", "")

        header = f"{cls}.{prop}".strip(".")
        type_str = f" [{ptype}]" if ptype else ""
        print(f"{header}{type_str}  (score={score:.3f})")
        print(text)
        print("-" * 60)

    if not final_matches:
        print("No attributes found for these parents.")
        print("-" * 60)

    return final_matches


# -----------------------------
# Fallback: global diverse attr query
# -----------------------------
def query_pinecone_diverse(
    query_text: str,
    namespace: str,
    top_k: int = 5,
    top_k_raw: int = 40,
    min_score: float | None = None,
):
    """
    Single-stage, 'diverse but specific' query on the attr namespace.

    - Query Pinecone with a larger top_k_raw.
    - Group by (className, propertyName).
    - Keep the best (highest score) per group.
    - Return top_k unique attributes, ranked by score.
    """
    vec = embed_query(query_text)

    res = index.query(
        vector=vec,
        top_k=top_k_raw,
        include_metadata=True,
        namespace=namespace,
    )

    matches = res.get("matches", [])

    grouped_best = {}  # key: (className, propertyName) -> best match

    for m in matches:
        md = m.get("metadata", {}) or {}
        cls = md.get("className")
        prop = md.get("propertyName")
        key = (cls, prop)

        if key not in grouped_best or m["score"] > grouped_best[key]["score"]:
            grouped_best[key] = m

    best_per_attr = list(grouped_best.values())
    best_per_attr.sort(key=lambda m: m["score"], reverse=True)

    if min_score is not None:
        best_per_attr = [m for m in best_per_attr if m["score"] >= min_score]

    final_matches = best_per_attr[:top_k]

    print(
        f"\n[Fallback] Global diverse attr query, top {len(final_matches)} "
        f"(namespace='{namespace}'):"
    )
    print("-" * 60)

    for m in final_matches:
        md = m.get("metadata", {}) or {}
        score = m.get("score", 0.0)
        cls = md.get("className", "")
        prop = md.get("propertyName", "")
        ptype = md.get("propertyType", "")
        text = md.get("text", "")

        header = f"{cls}.{prop}".strip(".")
        type_str = f" [{ptype}]" if ptype else ""
        print(f"{header}{type_str}  (score={score:.3f})")
        print(text)
        print("-" * 60)

    if not final_matches:
        print("No attributes found.")
        print("-" * 60)

    return final_matches


# -----------------------------
# Top-level: two-stage RAG query
# -----------------------------
def two_stage_rag_query(
    user_query: str,
    parent_namespace: str = "objects",
    attr_namespace: str = "object_attrs",
    top_k_parents: int = 5,
    top_k_attrs: int = 8,
    top_k_raw_attrs: int = 50,
):
    """
    Full two-stage retrieval pipeline:

    1) Use user_query to find likely parent objects in `parent_namespace`.
    2) Use the same user_query to find best attributes within those parents
       in `attr_namespace`, with diversity enforced across attributes.

    Returns:
        parents: list of parent object dicts
        attrs:   list of attribute match dicts (Pinecone matches)
    """
    parents = find_parent_objects(
        query_text=user_query,
        top_k_parents=top_k_parents,
        namespace=parent_namespace,
    )

    parent_names = [p["name"] for p in parents]

    attrs = query_attrs_for_parents(
        query_text=user_query,
        parent_names=parent_names,
        namespace=attr_namespace,
        top_k_attrs=top_k_attrs,
        top_k_raw=top_k_raw_attrs,
    )

    return parents, attrs


# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    user_query = "It seems to be running in the background but no command box is shown"

    parents, attrs = two_stage_rag_query(
        user_query=user_query,
        parent_namespace="objects",
        attr_namespace="object_attrs",
        top_k_parents=5,
        top_k_attrs=8,
        top_k_raw_attrs=50,
    )

    # 'parents' and 'attrs' can now be fed into your LLM as context for RAG.
