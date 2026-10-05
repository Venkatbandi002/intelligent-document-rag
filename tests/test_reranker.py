from backend.app.services.reranker import RerankerService


def test_reranker_scoring():
    reranker = RerankerService(top_n=2)
    query = "Titan Gateway hardware specifications"

    passages = [
        {
            "chunk_id": "c1",
            "document_name": "General_News.pdf",
            "page_number": 1,
            "content": "The cloud industry continues to experience high growth across multiple sectors.",
            "similarity_score": 0.65,
        },
        {
            "chunk_id": "c2",
            "document_name": "Product_Manual.pdf",
            "page_number": 1,
            "content": "Titan Gateway hardware specifications include 4 vCPU cores, 8 GB RAM, and 50 GB NVMe storage.",
            "similarity_score": 0.60,
        },
    ]

    reranked = reranker.rerank(query, passages, top_n=2)

    assert len(reranked) == 2
    # Product Manual with exact phrase matches should be promoted to #1 rank
    assert reranked[0]["chunk_id"] == "c2"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]
