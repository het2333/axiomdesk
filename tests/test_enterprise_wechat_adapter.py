from ai_employee.adapters.enterprise_wechat import EnterpriseWeChatAdapter


def test_adapter_normalizes_an_inbound_message_without_network_io() -> None:
    event = EnterpriseWeChatAdapter().to_event(
        {
            "message_id": "msg-1",
            "conversation_id": "thread-1",
            "external_user_id": "contact-1",
            "text": "交期多久",
        },
        organization_id="acme",
    )

    assert event.organization_id == "acme"
    assert event.customer_id == "contact-1"
    assert event.idempotency_key == "msg-1"
