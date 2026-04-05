import re

from config.db import get_db


def get_all_users():
    db = get_db()
    return list(db.users.find({}, {'password': 0}))


def find_user_by_email(email: str):
    db = get_db()
    return db.users.find_one({'email': email}, {'password': 0})


def search_users(query: str):
    db = get_db()
    safe_query = re.escape(query)
    return list(db.users.find(
        {'$or': [
            {'email': {'$regex': safe_query, '$options': 'i'}},
            {'first_name': {'$regex': safe_query, '$options': 'i'}},
            {'last_name': {'$regex': safe_query, '$options': 'i'}},
        ]},
        {'password': 0},
    ))


def count_users_by_role():
    db = get_db()
    pipeline = [
        {'$group': {'_id': '$role', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
    ]
    return list(db.users.aggregate(pipeline))
