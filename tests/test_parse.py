import pytest

from app.helpers import parse_metadata


DATA = [
    ("Test #me and @me", [], ["me"], [], ["me"]),
    ("Test https://subreply.com/", [], [], ["https://subreply.com/"], [])
]
IDS = ["Tags", "Link"]


@pytest.mark.parametrize("content,hashrefs,hashtags,links,mentions", DATA, ids=IDS)
def test_parse(content, hashrefs, hashtags, links, mentions):
    assert (hashrefs, hashtags, links, mentions) == parse_metadata(content)
