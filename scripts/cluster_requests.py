from unmet_demand.cluster.clusterer import cluster_requests
from unmet_demand.db import connect, init_db
from unmet_demand.embed.embedder import embed_requests


if __name__ == "__main__":
    init_db()
    with connect() as conn:
        embedding_backend = embed_requests(conn)
        clustering_backend = cluster_requests(conn)
    print(f"Embedded with {embedding_backend}; clustered with {clustering_backend}.")
