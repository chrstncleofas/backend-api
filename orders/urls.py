from django.urls import path
from orders.views import OrderListView, OrderDetailView, OrderStatusUpdateView, OrderReceiptUploadView

urlpatterns = [
    path('', OrderListView.as_view(), name='order-list'),
    path('<str:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('<str:order_id>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
    path('<str:order_id>/receipt/', OrderReceiptUploadView.as_view(), name='order-receipt-upload'),
]
