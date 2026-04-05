"""
Raw pymongo query examples for the orders collection.
Usage in Django shell: python manage.py shell
"""

from config.db import get_db


def get_customer_orders(customer_id: str):
    db = get_db()
    return list(db.orders.find({'customer_id': customer_id}).sort('created_at', -1))


def get_orders_by_status(order_status: str):
    db = get_db()
    return list(db.orders.find({'status': order_status}))


def get_merchant_revenue(merchant_id: str):
    db = get_db()
    pipeline = [
        {'$match': {'merchant_id': merchant_id, 'status': 'delivered'}},
        {'$group': {
            '_id': None,
            'total_revenue': {'$sum': '$total_amount'},
            'total_orders': {'$sum': 1},
            'avg_order_value': {'$avg': '$total_amount'},
        }},
    ]
    result = list(db.orders.aggregate(pipeline))
    return result[0] if result else None


def get_daily_order_stats(days: int = 7):
    db = get_db()
    from datetime import datetime, timedelta, timezone
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {'$match': {'created_at': {'$gte': start_date}}},
        {'$group': {
            '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
            'count': {'$sum': 1},
            'revenue': {'$sum': '$total_amount'},
        }},
        {'$sort': {'_id': 1}},
    ]
    return list(db.orders.aggregate(pipeline))


def get_popular_products(limit: int = 10):
    db = get_db()
    pipeline = [
        {'$unwind': '$items'},
        {'$group': {
            '_id': '$items.product_id',
            'product_name': {'$first': '$items.product_name'},
            'total_ordered': {'$sum': '$items.quantity'},
            'total_revenue': {'$sum': '$items.subtotal'},
        }},
        {'$sort': {'total_ordered': -1}},
        {'$limit': limit},
    ]
    return list(db.orders.aggregate(pipeline))
