import argparse

from unmet_demand.db import connect, init_db
from unmet_demand.ingest.discourse import DiscourseForumAdapter
from unmet_demand.ingest.github import GitHubIssuesAdapter
from unmet_demand.ingest.sources import insert_posts
from unmet_demand.ingest.stackexchange import StackExchangeAdapter


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import live public source search results.")
    parser.add_argument("source", choices=["discourse", "github", "stackexchange"])
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--base-url", help="Required for Discourse, for example https://forum.godotengine.org")
    parser.add_argument("--site", default="stackoverflow", help="Stack Exchange site, for example gamedev or stackoverflow")
    parser.add_argument("--requests-per-minute", type=int, default=20)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    args = parser.parse_args()

    if args.source == "discourse":
        if not args.base_url:
            raise SystemExit("--base-url is required for discourse")
        posts = DiscourseForumAdapter(
            args.base_url,
            requests_per_minute=args.requests_per_minute,
            max_retries=args.max_retries,
            backoff_seconds=args.backoff_seconds,
        ).search(args.query, limit=args.limit, pages=args.pages)
    elif args.source == "github":
        posts = GitHubIssuesAdapter(
            requests_per_minute=args.requests_per_minute,
            max_retries=args.max_retries,
            backoff_seconds=args.backoff_seconds,
        ).search(args.query, limit=args.limit, pages=args.pages)
    else:
        posts = StackExchangeAdapter(
            site=args.site,
            requests_per_minute=args.requests_per_minute,
            max_retries=args.max_retries,
            backoff_seconds=args.backoff_seconds,
        ).search(args.query, limit=args.limit, pages=args.pages)

    init_db()
    with connect() as conn:
        count = insert_posts(conn, posts)
    print(f"Imported {count} live {args.source} records.")
