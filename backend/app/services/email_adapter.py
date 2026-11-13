import logging

logger = logging.getLogger("datalens.email")


class DevEmailAdapter:
    """
    Development email adapter that logs emails to console
    and retains them in memory for automated test verification.
    """

    def __init__(self):
        self.sent_emails: list[dict[str, str]] = []

    def send_password_reset(self, to_email: str, reset_token: str) -> str:
        reset_url = f"http://localhost:5173/reset-password?token={reset_token}"
        message = {
            "to": to_email,
            "type": "password_reset",
            "token": reset_token,
            "url": reset_url,
        }
        self.sent_emails.append(message)
        logger.info(f"[DEV EMAIL] Password reset sent to {to_email}: {reset_url}")
        return reset_url

    def send_workspace_invitation(
        self, to_email: str, workspace_name: str, invitation_token: str, inviter_name: str
    ) -> str:
        invite_url = f"http://localhost:5173/invitations/accept?token={invitation_token}"
        message = {
            "to": to_email,
            "type": "workspace_invitation",
            "workspace_name": workspace_name,
            "inviter_name": inviter_name,
            "token": invitation_token,
            "url": invite_url,
        }
        self.sent_emails.append(message)
        logger.info(f"[DEV EMAIL] Invitation to '{workspace_name}' sent to {to_email}: {invite_url}")
        return invite_url

    def send_notification_email(
        self, to_email: str, subject: str, message: str, action_url: str | None = None
    ) -> dict[str, str]:
        email_record = {
            "to": to_email,
            "type": "notification",
            "subject": subject,
            "message": message,
            "url": action_url or "",
        }
        self.sent_emails.append(email_record)
        logger.info(f"[DEV EMAIL] Notification '{subject}' sent to {to_email}")
        return email_record

    def send_mention_email(
        self,
        to_email: str,
        mentioner_name: str,
        resource_type: str,
        resource_name: str,
        comment_snippet: str,
        action_url: str,
    ) -> dict[str, str]:
        subject = f"{mentioner_name} mentioned you in {resource_name}"
        email_record = {
            "to": to_email,
            "type": "mention",
            "subject": subject,
            "mentioner": mentioner_name,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "snippet": comment_snippet,
            "url": action_url,
        }
        self.sent_emails.append(email_record)
        logger.info(f"[DEV EMAIL] Mention notification sent to {to_email}: {subject}")
        return email_record

    def send_share_notification(
        self,
        to_email: str,
        shared_by_name: str,
        resource_type: str,
        resource_name: str,
        action_url: str,
    ) -> dict[str, str]:
        subject = f"{shared_by_name} shared a {resource_type} with you: {resource_name}"
        email_record = {
            "to": to_email,
            "type": "resource_share",
            "subject": subject,
            "shared_by": shared_by_name,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "url": action_url,
        }
        self.sent_emails.append(email_record)
        logger.info(f"[DEV EMAIL] Share notification sent to {to_email}: {subject}")
        return email_record

    def get_latest_reset_token(self, email: str) -> str | None:
        for msg in reversed(self.sent_emails):
            if msg.get("to") == email and msg.get("type") == "password_reset":
                return msg.get("token")
        return None

    def get_latest_invitation_token(self, email: str) -> str | None:
        for msg in reversed(self.sent_emails):
            if msg.get("to") == email and msg.get("type") == "workspace_invitation":
                return msg.get("token")
        return None

    def clear(self):
        self.sent_emails.clear()


dev_email_adapter = DevEmailAdapter()
