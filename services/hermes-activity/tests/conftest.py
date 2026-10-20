from typing import Never

import pytest


@pytest.fixture(autouse=True)
def forbid_real_desktop_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*, xdisplay: str | None = None) -> Never:
        _ = xdisplay
        pytest.fail("non-live verification attempted desktop capture")

    monkeypatch.setattr("screen.ImageGrab.grab", forbidden)
