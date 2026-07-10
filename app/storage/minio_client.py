from minio import Minio
from minio.error import S3Error
from app.config import settings
import os
import logging
from typing import Optional

logger = logging.getLogger("securecode.storage")


class MinioClient:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Bucket '{self.bucket}' creado")
        except S3Error as e:
            logger.warning(f"Error al crear bucket MinIO: {e}")

    def upload_file(self, local_path: str, object_name: Optional[str] = None) -> str:
        if not object_name:
            object_name = os.path.basename(local_path)

        try:
            self.client.fput_object(self.bucket, object_name, local_path)
            logger.info(f"Archivo subido: {object_name}")
            return f"{settings.MINIO_ENDPOINT}/{self.bucket}/{object_name}"
        except S3Error as e:
            logger.error(f"Error subiendo archivo a MinIO: {e}")
            raise

    def download_file(self, object_name: str, local_path: str):
        try:
            self.client.fget_object(self.bucket, object_name, local_path)
            logger.info(f"Archivo descargado: {object_name}")
        except S3Error as e:
            logger.error(f"Error descargando archivo de MinIO: {e}")
            raise

    def list_files(self, prefix: str = "") -> list:
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            return [{"name": obj.object_name, "size": obj.size, "last_modified": obj.last_modified} for obj in objects]
        except S3Error as e:
            logger.error(f"Error listando archivos: {e}")
            return []

    def delete_file(self, object_name: str):
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info(f"Archivo eliminado: {object_name}")
        except S3Error as e:
            logger.error(f"Error eliminando archivo: {e}")
            raise


class FileManager:
    def __init__(self):
        self.minio = MinioClient()
        self.local_dir = settings.APP_UPLOAD_DIR
        os.makedirs(self.local_dir, exist_ok=True)

    def save_upload(self, file_content: bytes, filename: str) -> str:
        local_path = os.path.join(self.local_dir, filename)
        with open(local_path, "wb") as f:
            f.write(file_content)
        return local_path

    def save_report(self, local_path: str, report_type: str, audit_id: int) -> str:
        object_name = f"reports/{audit_id}/{report_type}/{os.path.basename(local_path)}"
        return self.minio.upload_file(local_path, object_name)

    def get_report_url(self, audit_id: int, report_type: str, filename: str) -> str:
        return f"reports/{audit_id}/{report_type}/{filename}"
