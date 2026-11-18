from django.urls import path
from .views import NotificationListView, mark_notification_read, mark_all_notifications_read

app_name = 'core'

urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/<uuid:pk>/read/', mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', mark_all_notifications_read, name='mark_all_notifications_read'),
]
