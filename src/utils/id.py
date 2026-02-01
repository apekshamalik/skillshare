from bson import ObjectId

def generate_objectid() -> str:
    """Generate a MongoDB ObjectId string"""
    
    return str(ObjectId())