import re

file_path = '/root/workspace/JMCDonations_fastapi/app/api/v1/donations.py'
with open(file_path, 'r') as f:
    content = f.read()

if 'from app.services.aws import upload_file_to_s3' not in content:
    content = 'from app.services.aws import upload_file_to_s3\nimport re\n' + content

old_code = """    upload_dir = Path("static/donations")
    upload_dir.mkdir(parents=True, exist_ok=True)

    current_images = list(donation.image_urls or [])
    for idx, f in enumerate(incoming_files):
        if not f.content_type or not f.content_type.startswith("image/"):
            continue
        ext = f.filename.split(".")[-1] if f.filename and "." in f.filename else "jpg"
        timestamp = int(datetime.now(timezone.utc).timestamp())
        filename = f"{donation_id}_{timestamp}_{idx}_{uuid.uuid4().hex[:6]}.{ext}"
        dest_path = upload_dir / filename

        content = await f.read()
        with open(dest_path, "wb") as out_file:
            out_file.write(content)

        relative_url = f"/static/donations/{filename}"
        current_images.append(relative_url)"""

new_code = """    safe_title = re.sub(r'[^a-zA-Z0-9]+', '-', donation.title).strip('-').lower()
    if not safe_title:
        safe_title = "drive"

    current_images = list(donation.image_urls or [])
    for idx, f in enumerate(incoming_files):
        if not f.content_type or not f.content_type.startswith("image/"):
            continue
        ext = f.filename.split(".")[-1] if f.filename and "." in f.filename else "jpg"
        timestamp = int(datetime.now(timezone.utc).timestamp())
        filename = f"{timestamp}_{idx}_{uuid.uuid4().hex[:6]}.{ext}"
        object_name = f"donations_gallery/{safe_title}/{filename}"

        try:
            public_url = upload_file_to_s3(f.file, object_name, content_type=f.content_type)
            current_images.append(public_url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload image to S3: {str(e)}")"""

content = content.replace(old_code, new_code)

with open(file_path, 'w') as f:
    f.write(content)
