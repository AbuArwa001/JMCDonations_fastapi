import boto3
from typing import Optional
from app.core.config import settings

def get_s3_client():
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        return None
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

def upload_file_to_s3(file_obj, object_name: str, content_type: Optional[str] = None) -> str:
    """
    Uploads a file object to AWS S3 and returns the public URL.
    """
    s3_client = get_s3_client()
    if not s3_client:
        raise ValueError("AWS credentials not configured")
        
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    extra_args = {}
    if content_type:
        extra_args['ContentType'] = content_type
        
    s3_client.upload_fileobj(file_obj, bucket, object_name, ExtraArgs=extra_args)
    
    # Generate public S3 URL
    return f"https://{bucket}.s3.amazonaws.com/{object_name}"

def delete_file_from_s3(object_name: str) -> bool:
    """
    Deletes an object from AWS S3.
    """
    s3_client = get_s3_client()
    if not s3_client:
        return False
        
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    try:
        s3_client.delete_object(Bucket=bucket, Key=object_name)
        return True
    except Exception as e:
        print(f"Error deleting {object_name} from S3: {e}")
        return False
