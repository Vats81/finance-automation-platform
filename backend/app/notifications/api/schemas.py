from typing import Literal

from pydantic import BaseModel

from app.notifications.application.queries.list_notifications import Notification, Notifications


class NotificationResponse(BaseModel):
    id: str
    category: Literal["overdue_sale", "overdue_purchase", "low_stock"]
    severity: Literal["warning", "critical"]
    message: str
    link: str

    @classmethod
    def from_domain(cls, notification: Notification) -> "NotificationResponse":
        return cls(
            id=notification.id,
            category=notification.category,
            severity=notification.severity,
            message=notification.message,
            link=notification.link,
        )


class NotificationsResponse(BaseModel):
    count: int
    items: list[NotificationResponse]

    @classmethod
    def from_domain(cls, notifications: Notifications) -> "NotificationsResponse":
        return cls(
            count=notifications.count,
            items=[NotificationResponse.from_domain(n) for n in notifications.items],
        )
