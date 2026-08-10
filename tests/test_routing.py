"""Tests for the Digitransit routing request headers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from hsl_kaupunkipyora_exporter.routing import USER_AGENT, fetch_route


def _mock_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__.return_value = resp
    return resp


@patch("hsl_kaupunkipyora_exporter.routing.urllib.request.urlopen")
def test_fetch_route_sets_user_agent(mock_urlopen: MagicMock) -> None:
    mock_urlopen.return_value = _mock_response({"data": {"plan": {"itineraries": []}}})

    fetch_route(60.17, 24.93, 60.18, 24.94, api_key="test-key")

    req = mock_urlopen.call_args[0][0]
    assert req.get_header("User-agent") == USER_AGENT
    assert req.get_header("Digitransit-subscription-key") == "test-key"
