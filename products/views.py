import logging
from botocore.exceptions import ClientError
from rest_framework import status
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser
from drf_spectacular.utils import extend_schema, OpenApiParameter

from config.s3 import s3_service
from config.serializers import MultiFileUploadSerializer
from products.documents import Product
from products.serializers import ProductSerializer, ProductCreateSerializer, ProductUpdateSerializer

logger = logging.getLogger(__name__)


def _safe_page(request: Request, default: int = 1) -> int:
    try:
        page = int(request.query_params.get('page', default))
        return max(1, page)
    except (ValueError, TypeError):
        return default


class ProductListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='category', type=str, required=False),
            OpenApiParameter(name='search', type=str, required=False),
            OpenApiParameter(name='page', type=int, required=False),
        ],
        responses={200: ProductSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        queryset = Product.objects(is_available=True)

        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        # Safe pagination
        page = _safe_page(request)
        page_size = 20
        start = (page - 1) * page_size
        products = queryset[start:start + page_size]

        return Response(
            {
                'success': True,
                'data': ProductSerializer(products, many=True).data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': queryset.count(),
                },
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=ProductCreateSerializer, responses={201: ProductSerializer})
    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        product = Product(
            merchant_id=str(request.user.id),
            **data,
        )
        product.save()

        return Response(
            {'success': True, 'data': ProductSerializer(product).data},
            status=status.HTTP_201_CREATED,
        )


class ProductDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def _get_product(self, product_id):
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return None

    @extend_schema(responses={200: ProductSerializer})
    def get(self, request, product_id):
        product = self._get_product(product_id)
        if not product:
            return Response(
                {'success': False, 'error': 'Product not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {'success': True, 'data': ProductSerializer(product).data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=ProductUpdateSerializer, responses={200: ProductSerializer})
    def patch(self, request: Request, product_id: str) -> Response:
        product = self._get_product(product_id)
        if not product:
            return Response(
                {'success': False, 'error': 'Product not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only the merchant who owns the product can update it
        if product.merchant_id != str(request.user.id):
            return Response(
                {'success': False, 'error': 'Not authorized to update this product.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate through serializer before applying
        serializer = ProductUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for field, value in serializer.validated_data.items():
            setattr(product, field, value)

        product.save()

        return Response(
            {'success': True, 'data': ProductSerializer(product).data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={204: None})
    def delete(self, request, product_id):
        product = self._get_product(product_id)
        if not product:
            return Response(
                {'success': False, 'error': 'Product not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if product.merchant_id != str(request.user.id):
            return Response(
                {'success': False, 'error': 'Not authorized to delete this product.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        product.delete()

        return Response(
            {'success': True, 'message': 'Product deleted.'},
            status=status.HTTP_200_OK,
        )


class ProductImageUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def _get_owned_product(self, request: Request, product_id: str) -> Product | None:
        """Return product if it exists and belongs to the requesting merchant."""
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return None
        if product.merchant_id != str(request.user.id):
            return None
        return product

    @extend_schema(
        request=MultiFileUploadSerializer,
        responses={200: ProductSerializer},
        description='Upload 1–10 images (JPEG, PNG, WebP, 5–25 MB each).',
    )
    def post(self, request: Request, product_id: str) -> Response:
        product = self._get_owned_product(request, product_id)
        if not product:
            return Response(
                {'success': False, 'error': 'Product not found or not authorized.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = MultiFileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_urls: list[str] = []
        for file in serializer.validated_data['files']:
            try:
                result = s3_service.upload_image(file, f"products/{product_id}")
                uploaded_urls.append(result['url'])
            except ValueError as exc:
                return Response(
                    {'success': False, 'error': str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except ClientError:
                logger.exception("S3 upload failed for product %s", product_id)
                return Response(
                    {'success': False, 'error': 'File upload failed. Try again.'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        product.images.extend(uploaded_urls)
        product.save()

        return Response(
            {'success': True, 'data': ProductSerializer(product).data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        description='Delete an image by its S3 URL.',
        responses={200: ProductSerializer},
    )
    def delete(self, request: Request, product_id: str) -> Response:
        product = self._get_owned_product(request, product_id)
        if not product:
            return Response(
                {'success': False, 'error': 'Product not found or not authorized.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        image_url = request.data.get('image_url', '')
        if image_url not in product.images:
            return Response(
                {'success': False, 'error': 'Image URL not found on this product.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract S3 key from URL and delete
        s3_service.delete_file_by_url(image_url)

        product.images.remove(image_url)
        product.save()

        return Response(
            {'success': True, 'data': ProductSerializer(product).data},
            status=status.HTTP_200_OK,
        )
