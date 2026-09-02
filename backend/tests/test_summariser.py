from unittest.mock import MagicMock

from services import summariser


def _mock_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    response.status_code = 200
    return response


def test_no_sdg_signal_is_valid_short_output():
    result = summariser._validate_output(
        "NO_SDG_SIGNAL",
        name="generic-lib",
        description="A reusable software library",
        topics=["python"],
    )

    assert result == "NO_SDG_SIGNAL"


def test_gpt_oss_payload_uses_low_reasoning_effort(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return _mock_response({
            "choices": [{
                "finish_reason": "stop",
                "message": {
                    "content": (
                        "Health record management supports clinics in low-resource "
                        "settings. Patients and healthcare workers benefit from "
                        "more consistent treatment histories. The work addresses "
                        "care continuity and service delivery gaps. Its impact is "
                        "strongest in public health and clinical operations."
                    ),
                },
            }],
        })

    monkeypatch.setattr(summariser.requests, "post", fake_post)

    result = summariser.summarize_for_sdg(
        readme="OpenMRS supports clinics and ministries of health.",
        name="OpenMRS",
        description="Medical records for resource-constrained settings",
        topics=["healthcare"],
        api_key="test-key",
    )

    assert captured["json"]["reasoning_effort"] == "low"
    assert "Health record management" in result
