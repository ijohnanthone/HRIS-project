from django.urls import path
from .views import (
    COERequestListView,
    MyCOERequestsView,
    COERequestCreateView,
    COERequestDetailView,
    COEApprovalProcessView,
    COEDocumentDownloadView,
    COETemplateManageView,
)

app_name = 'requests'

urlpatterns = [
    path('coe/', COERequestListView.as_view(), name='coe_list'),
    path('coe/my/', MyCOERequestsView.as_view(), name='my_requests'),
    path('coe/create/', COERequestCreateView.as_view(), name='coe_create'),
    path('coe/<uuid:pk>/', COERequestDetailView.as_view(), name='coe_detail'),
    path('coe/<uuid:pk>/decision/', COEApprovalProcessView.as_view(), name='coe_decision'),
    path('coe/<uuid:pk>/download/', COEDocumentDownloadView.as_view(), name='coe_download'),
    path('coe/templates/', COETemplateManageView.as_view(), name='coe_templates'),
]
