from src.agent_api.chat_cli import print_response


def test_print_response_outputs_answer_metadata(capsys):
    print_response(
        {
            "answer": "Clear browser cache and retry SSO login.",
            "citations": [
                {
                    "doc_id": "sso_login_troubleshooting",
                    "chunk_id": "sso_login_troubleshooting#003",
                }
            ],
            "next_actions": ["Ask whether MFA enrollment is complete."],
            "ticket_draft": {"created": True, "draft_id": "draft-123"},
        }
    )

    output = capsys.readouterr().out
    assert "Clear browser cache and retry SSO login." in output
    assert "sso_login_troubleshooting / sso_login_troubleshooting#003" in output
    assert "Ask whether MFA enrollment is complete." in output
    assert "draft-123" in output
