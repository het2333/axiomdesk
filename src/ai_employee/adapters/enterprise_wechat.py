from collections.abc import Mapping

from ai_employee.contracts import ConversationEvent


class EnterpriseWeChatAdapter:
    def to_event(self, payload: Mapping[str, str], organization_id: str) -> ConversationEvent:
        return ConversationEvent(
            organization_id=organization_id,
            conversation_id=payload["conversation_id"],
            customer_id=payload["external_user_id"],
            message=payload["text"],
            idempotency_key=payload["message_id"],
        )
