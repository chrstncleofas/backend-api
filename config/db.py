from mongoengine.connection import get_db as _mongoengine_get_db
def get_db():
    """Return the PyMongo Database object from MongoEngine's managed connection."""
    return _mongoengine_get_db()
