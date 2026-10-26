import pytest

from app.meetings.meeting_url import UnsupportedPlatform, normalize_meet_url


@pytest.mark.parametrize("url,expected", [
    ("https://meet.google.com/abc-defg-hij", "https://meet.google.com/abc-defg-hij"),
    ("https://meet.google.com/abc-defg-hij?authuser=0", "https://meet.google.com/abc-defg-hij"),
    ("https://meet.google.com/abc-defg-hij#frag", "https://meet.google.com/abc-defg-hij"),
    ("  https://meet.google.com/xyz-abcd-efg  ", "https://meet.google.com/xyz-abcd-efg"),
])
def test_accepts_meet_links_and_strips_query(url, expected):
    assert normalize_meet_url(url) == expected


@pytest.mark.parametrize("url", [
    "https://zoom.us/j/123456789",
    "https://us02web.zoom.us/j/123456789",
    "https://teams.microsoft.com/l/meetup-join/19%3ameeting",
    "https://teams.live.com/meet/123",
    "http://meet.google.com/abc-defg-hij",
    "meet.google.com/abc-defg-hij",
    "https://meet.google.com.evil.com/abc-defg-hij",
    "https://evilmeet.google.com/abc-defg-hij",
    "https://meet.google.com@evil.com/abc-defg-hij",
    "https://user:pass@meet.google.com/abc-defg-hij",
    "https://meet.google.com:8443/abc-defg-hij",
    "https://meet.google.com/",
    "https://meet.google.com/abc-defg",
    "https://meet.google.com/ABC-DEFG-HIJ",
    "https://meet.google.com/abc-defg-hij/lookup/xyz",
    "https://meet.google.com/abc-defg-hij/../admin",
    "https://meet.google.com/%61bc-defg-hij",
    "https://meet.google.com/abc%2Ddefg%2Dhij",
    "https://meet.google.com/abcdefghij",
    "https://meet.google.co/abc-defg-hij",
    "ftp://meet.google.com/abc-defg-hij",
    "javascript:alert(1)",
    "https://m\u0435et.google.com/abc-defg-hij",
    "",
])
def test_rejects_everything_that_is_not_a_meet_link(url):
    with pytest.raises(UnsupportedPlatform):
        normalize_meet_url(url)


def test_error_carries_the_contract_code_and_message():
    with pytest.raises(UnsupportedPlatform) as excinfo:
        normalize_meet_url("https://zoom.us/j/1")
    assert excinfo.value.code == "unsupported_platform"
    assert str(excinfo.value) == "Only Google Meet links (meet.google.com) are supported."
