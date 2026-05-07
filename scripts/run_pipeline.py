from unmet_demand.cluster.clusterer import cluster_requests
from unmet_demand.db import connect, init_db
from unmet_demand.embed.embedder import embed_requests
from unmet_demand.extract.extractor import extract_requests
from unmet_demand.ingest.sample_loader import load_sample_posts
from unmet_demand.score.scorer import score_clusters


if __name__ == "__main__":
    init_db()
    with connect() as conn:
        posts = load_sample_posts(conn)
        requests = extract_requests(conn)
        embedding_backend = embed_requests(conn)
        clustering_backend = cluster_requests(conn)
        clusters = score_clusters(conn)
    print(
        "Pipeline complete: "
        f"{posts} posts, {requests} extracted requests, {clusters} scored clusters "
        f"(embeddings={embedding_backend}, clustering={clustering_backend})."
    )
