import logging
from decimal import Decimal
from botocore.exceptions import ClientError
from rest_framework import status
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from drf_spectacular.utils import extend_schema, OpenApiParameter

from config.s3 import s3_service
from config.serializers import FileUploadSerializer
from orders.documents import Order, OrderItem
from orders.serializers import (
    OrderSerializer,
    OrderCreateSerializer,
    OrderStatusUpdateSerializer,
)
from products.documents import Product

logger = logging.getLogger(__name__)

# Valid status transitions per role
STATUS_TRANSITIONS: dict[str, dict[str, list[str]]] = {
    'merchant': {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'cancelled'],
        'preparing': ['ready_for_pickup'],
    },
    'rider': {
        'ready_for_pickup': ['picked_up'],
        'picked_up': ['delivering'],
        'delivering': ['delivered'],
    },
    'customer': {
        'pending': ['cancelled'],
    },
}


def _is_order_participant(user, order: Order) -> bool:
    """Check if the user is a participant (customer, merchant, or rider) of this order."""
    user_id = str(user.id)
    return user_id in [order.customer_id, order.merchant_id, order.rider_id]


def _safe_page(request: Request, default: int = 1) -> int:
    """Safely parse page number from query params."""
    try:
        page = int(request.query_params.get('page', default))
        return max(1, page)
    except (ValueError, TypeError):
        return default


class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='status', type=str, required=False),
            OpenApiParameter(name='page', type=int, required=False),
        ],
        responses={200: OrderSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        user = request.user
        user_id = str(user.id)

        # Show orders based on user role
        if user.role == 'merchant':
            queryset = Order.objects(merchant_id=user_id)
        elif user.role == 'rider':
            queryset = Order.objects(rider_id=user_id)
        else:
            queryset = Order.objects(customer_id=user_id)

        order_status = request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status)

        # Pagination
        page = _safe_page(request)
        page_size = 20
        start = (page - 1) * page_size
        orders = queryset[start:start + page_size]

        return Response(
            {
                'success': True,
                'data': OrderSerializer(orders, many=True).data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': queryset.count(),
                },
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=OrderCreateSerializer, responses={201: OrderSerializer})
    def post(self, request: Request) -> Response:
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Collect product IDs and look up actual prices from DB
        product_ids = [item['product_id'] for item in data['items']]
        products = {str(p.id): p for p in Product.objects(id__in=product_ids, is_available=True)}

        # Validate all products exist
        missing = set(product_ids) - set(products.keys())
        if missing:
            return Response(
                {'success': False, 'error': f'Products not found: {", ".join(missing)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build order items using server-side prices (never trust client)
        order_items = []
        total_amount = Decimal('0')

        for item_data in data['items']:
            product = products[item_data['product_id']]
            server_price = product.price
            subtotal = Decimal(str(server_price)) * item_data['quantity']
            order_item = OrderItem(
                product_id=item_data['product_id'],
                product_name=product.name,
                quantity=item_data['quantity'],
                price=server_price,
                subtotal=subtotal,
            )
            order_items.append(order_item)
            total_amount += subtotal

        total_amount += Decimal(str(data.get('delivery_fee', 0)))

        order = Order(
            customer_id=str(request.user.id),
            merchant_id=data['merchant_id'],
            items=order_items,
            total_amount=total_amount,
            delivery_fee=data.get('delivery_fee', 0),
            delivery_address=data.get('delivery_address', ''),
            notes=data.get('notes', ''),
        )
        order.save()

        logger.info("Order %s created by user %s (₱%s)", order.id, request.user.id, total_amount)

        return Response(
            {'success': True, 'data': OrderSerializer(order).data},
            status=status.HTTP_201_CREATED,
        )


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_order(self, order_id: str) -> Order | None:
        try:
            return Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return None

    @extend_schema(responses={200: OrderSerializer})
    def get(self, request: Request, order_id: str) -> Response:
        order = self._get_order(order_id)
        if not order:
            return Response(
                {'success': False, 'error': 'Order not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Ownership check — only involved parties can view
        if not _is_order_participant(request.user, order):
            return Response(
                {'success': False, 'error': 'Not authorized to view this order.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {'success': True, 'data': OrderSerializer(order).data},
            status=status.HTTP_200_OK,
        )


class OrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=OrderStatusUpdateSerializer, responses={200: OrderSerializer})
    def patch(self, request: Request, order_id: str) -> Response:
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Order not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Must be a participant
        if not _is_order_participant(request.user, order):
            return Response(
                {'success': False, 'error': 'Not authorized to update this order.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        role = request.user.role

        # Validate status transition based on role
        allowed = STATUS_TRANSITIONS.get(role, {}).get(order.status, [])
        if new_status not in allowed:
            return Response(
                {
                    'success': False,
                    'error': f'{role} cannot change status from "{order.status}" to "{new_status}".',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        old_status = order.status
        order.status = new_status
        order.save()

        logger.info(
            "Order %s status: %s → %s (by %s, role=%s)",
            order_id, old_status, new_status, request.user.id, role,
        )

        return Response(
            {'success': True, 'data': OrderSerializer(order).data},
            status=status.HTTP_200_OK,
        )


# Statuses that allow receipt upload (proof of delivery)
RECEIPT_UPLOAD_STATUSES: set[str] = {'delivering', 'delivered'}


class OrderReceiptUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    @extend_schema(
        request=FileUploadSerializer,
        responses={200: OrderSerializer},
        description='Upload proof of delivery (image or PDF, 5–25 MB). Rider or merchant only.',
    )
    def post(self, request: Request, order_id: str) -> Response:
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Order not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only rider or merchant can upload receipt
        user_id = str(request.user.id)
        if user_id not in [order.merchant_id, order.rider_id]:
            return Response(
                {'success': False, 'error': 'Not authorized to upload receipt for this order.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if order.status not in RECEIPT_UPLOAD_STATUSES:
            return Response(
                {'success': False, 'error': f'Cannot upload receipt when order status is "{order.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delete old receipt if re-uploading
        if order.receipt_url:
            s3_service.delete_file_by_url(order.receipt_url)

        try:
            result = s3_service.upload_document(
                serializer.validated_data['file'],
                f"orders/{order_id}",
            )
        except ValueError as exc:
            return Response(
                {'success': False, 'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ClientError:
            logger.exception("S3 receipt upload failed for order %s", order_id)
            return Response(
                {'success': False, 'error': 'File upload failed. Try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        order.receipt_url = result['url']
        order.save()

        logger.info("Receipt uploaded for order %s by user %s", order_id, user_id)

        return Response(
            {'success': True, 'data': OrderSerializer(order).data},
            status=status.HTTP_200_OK,
        )
