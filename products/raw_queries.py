"""
Raw pymongo query examples for the products collection.
Usage in Django shell: python manage.py shell
"""

from config.db import get_db


def get_products_by_category(category: str):
    db = get_db()
    return list(db.products.find({'category': category, 'is_available': True}))


def get_merchant_products(merchant_id: str):
    db = get_db()
    return list(db.products.find({'merchant_id': merchant_id}))


def full_text_search(query: str):
    db = get_db()
    # Requires text index: db.products.createIndex({name: "text", description: "text"})
    return list(db.products.find({'$text': {'$search': query}}))


def get_price_stats_by_category():
    db = get_db()
    pipeline = [
        {'$match': {'is_available': True}},
        {'$group': {
            '_id': '$category',
            'avg_price': {'$avg': '$price'},
            'min_price': {'$min': '$price'},
            'max_price': {'$max': '$price'},
            'count': {'$sum': 1},
        }},
        {'$sort': {'count': -1}},
    ]
    return list(db.products.aggregate(pipeline))


def get_low_stock_products(threshold: int = 5):
    db = get_db()
    return list(db.products.find(
        {'stock': {'$lte': threshold}, 'is_available': True},
        {'name': 1, 'stock': 1, 'merchant_id': 1},
    ))
