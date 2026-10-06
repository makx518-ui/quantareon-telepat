from telepat.security.rate_limit import FixedWindowRateLimiter


def test_rate_limiter_allows_up_to_limit_then_blocks() -> None:
    limiter = FixedWindowRateLimiter(
        window_seconds=60,
        max_entries=100,
    )

    assert limiter.allow("chat", "user-a", limit=2, now=0) is True
    assert limiter.allow("chat", "user-a", limit=2, now=1) is True
    assert limiter.allow("chat", "user-a", limit=2, now=2) is False


def test_rate_limiter_resets_after_window() -> None:
    limiter = FixedWindowRateLimiter(
        window_seconds=10,
        max_entries=100,
    )

    assert limiter.allow("astro", "user-a", limit=1, now=0) is True
    assert limiter.allow("astro", "user-a", limit=1, now=5) is False
    assert limiter.allow("astro", "user-a", limit=1, now=11) is True


def test_rate_limiter_scopes_are_independent() -> None:
    limiter = FixedWindowRateLimiter(
        window_seconds=60,
        max_entries=100,
    )

    assert limiter.allow("chat", "same-user", limit=1, now=0) is True
    assert limiter.allow("voice", "same-user", limit=1, now=0) is True
