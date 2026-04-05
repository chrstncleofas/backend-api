"""
Shared database utility for raw PyMongo access.

Reuses the MongoEngine connection instead of creating a new MongoClient per call.

Usage:
    from config.db import get_db
    db = get_db()
    db.users.find({})
"""

from mongoengine.connection import get_db as _mongoengine_get_db


def get_db():
    """Return the PyMongo Database object from MongoEngine's managed connection."""
    return _mongoengine_get_db()
