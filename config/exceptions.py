import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            'success': False,
            'error': {
                'status_code': response.status_code,
                'detail': response.data,
            }
        }
        return response

    # Unhandled exceptions — log the full traceback
    view = context.get('view', None)
    logger.exception(
        "Unhandled exception in %s: %s",
        view.__class__.__name__ if view else 'unknown',
        exc,
    )

    return Response(
        {
            'success': False,
            'error': {
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'detail': 'An unexpected error occurred.',
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
