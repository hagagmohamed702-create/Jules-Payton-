from django.urls import path
from ..views import notifications

app_name = 'notifications'

urlpatterns = [
    path('', notifications.notification_list, name='notification_list'),
    path('<int:pk>/', notifications.notification_detail, name='notification_detail'),
    path('<int:pk>/read/', notifications.mark_as_read, name='mark_as_read'),
    path('mark-all-read/', notifications.mark_all_as_read, name='mark_all_as_read'),
    path('<int:pk>/delete/', notifications.delete_notification, name='delete_notification'),
    path('delete-read/', notifications.delete_read_notifications, name='delete_read_notifications'),
    path('settings/', notifications.notification_settings, name='notification_settings'),
    path('popup/', notifications.notification_popup, name='notification_popup'),
    path('check-new/', notifications.check_new_notifications, name='check_new_notifications'),
]