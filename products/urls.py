from django.urls import path
from products.views import ProductListView, ProductDetailView, ProductImageUploadView

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('<str:product_id>/', ProductDetailView.as_view(), name='product-detail'),
    path('<str:product_id>/images/', ProductImageUploadView.as_view(), name='product-images'),
]
