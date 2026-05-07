from unmet_demand.ingest.discourse import DiscourseForumAdapter
from unmet_demand.ingest.github import GitHubIssuesAdapter
from unmet_demand.ingest.stackexchange import StackExchangeAdapter


def test_discourse_normalizes_search_payload():
    adapter = DiscourseForumAdapter("https://forum.example.test")
    posts = adapter._normalize_search_results(
        {
            "topics": [{"id": 10, "title": "Need a plugin", "slug": "need-plugin"}],
            "posts": [{"id": 99, "topic_id": 10, "post_number": 1, "username": "dev", "blurb": "I wish there was a tool"}],
        },
        limit=10,
    )

    assert posts[0].source_type == "forum"
    assert posts[0].title == "Need a plugin"
    assert "tool" in posts[0].body


def test_github_normalizes_issue_items():
    adapter = GitHubIssuesAdapter()
    posts = adapter._normalize_items(
        [
            {
                "id": 1,
                "title": "Add exporter",
                "body": "I wish there was a Godot exporter",
                "html_url": "https://github.com/o/r/issues/1",
                "user": {"login": "dev"},
            }
        ]
    )

    assert posts[0].source_type == "github"
    assert posts[0].author == "dev"


def test_stackexchange_normalizes_items():
    adapter = StackExchangeAdapter(site="gamedev")
    posts = adapter._normalize_items(
        [
            {
                "question_id": 1,
                "title": "Tool request",
                "body": "Looking for a tool that audits assets",
                "link": "https://gamedev.stackexchange.com/q/1",
                "owner": {"display_name": "dev"},
            }
        ]
    )

    assert posts[0].source_type == "stackexchange"
    assert posts[0].source == "stackexchange:gamedev"
