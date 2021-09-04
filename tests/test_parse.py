import pytest

from app.helpers import parse_metadata


@pytest.mark.parametrize("content,mentions,links,hashtags", [
    ("Test #me and @me", ["me"], [], ["me"]),
    ("Test https://subreply.com/", [], ["https://subreply.com/"], [])
], ids=["Tags", "Link"])
def test_parse(content, mentions, links, hashtags):
    assert (mentions, links, hashtags) == parse_metadata(content)
