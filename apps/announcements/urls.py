from django.urls import path
from .views import (
    AnnouncementListView,
    AnnouncementCreateView,
    AnnouncementDetailView,
)

app_name = 'announcements'

urlpatterns = [
    path('', AnnouncementListView.as_view(), name='list'),
    path('create/', AnnouncementCreateView.as_view(), name='create'),
    path('<int:pk>/', AnnouncementDetailView.as_view(), name='detail'),
]
