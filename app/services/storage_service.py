import hashlib
import logging
import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator, Iterator, Optional, TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from app.models.exame import Exame

logger = logging.getLogger(__name__)


@dataclass
class StoredFileMetadata:
    storage_provider: str
    storage_bucket: Optional[str]
    storage_object_key: str
    storage_content_type: str
    storage_size_bytes: int
    storage_checksum: str
    storage_status: str
    url_documento: str


@dataclass
class FileDownload:
    chunks: Iterator[bytes]
    content_type: str
    size_bytes: Optional[int]
    original_filename: Optional[str]


class StorageUnavailableError(RuntimeError):
    pass


class ExamStorageService:
    def __init__(self) -> None:
        self.backend = settings.OCR_STORAGE_BACKEND.lower()
        self.bucket = settings.OCR_STORAGE_BUCKET
        self.local_storage_dir = settings.OCR_LOCAL_STORAGE_DIR
        self._s3_client = None

    def store_file(
        self,
        *,
        source_path: str,
        patient_id: int,
        original_filename: Optional[str],
        content_type: Optional[str],
    ) -> StoredFileMetadata:
        file_extension = os.path.splitext(original_filename or source_path)[1] or ".pdf"
        object_key = f"patients/{patient_id}/{uuid.uuid4()}{file_extension.lower()}"
        checksum = self._calculate_checksum(source_path)
        size_bytes = os.path.getsize(source_path)
        normalized_content_type = content_type or "application/pdf"

        if self.backend == "s3":
            return self._store_file_s3(
                source_path=source_path,
                object_key=object_key,
                content_type=normalized_content_type,
                checksum=checksum,
                size_bytes=size_bytes,
            )

        return self._store_file_local(
            source_path=source_path,
            object_key=object_key,
            content_type=normalized_content_type,
            checksum=checksum,
            size_bytes=size_bytes,
        )

    def delete_file(self, metadata: StoredFileMetadata) -> None:
        try:
            if metadata.storage_provider == "s3":
                client = self._get_s3_client()
                client.delete_object(
                    Bucket=metadata.storage_bucket or self.bucket,
                    Key=metadata.storage_object_key,
                )
                return

            os.remove(metadata.storage_object_key)
        except FileNotFoundError:
            return
        except OSError as exc:
            logger.warning("Falha ao remover arquivo persistido %s: %s", metadata.storage_object_key, exc)

    def stream_file(self, exame: Any) -> FileDownload:
        legacy_path = self._resolve_legacy_local_path(exame)
        if legacy_path:
            return FileDownload(
                chunks=self._iter_local_file(legacy_path),
                content_type=exame.storage_content_type or "application/pdf",
                size_bytes=exame.storage_size_bytes or os.path.getsize(legacy_path),
                original_filename=exame.original_filename,
            )

        provider = (exame.storage_provider or "").lower()
        if provider == "s3":
            client = self._get_s3_client()
            response = client.get_object(
                Bucket=exame.storage_bucket or self.bucket,
                Key=exame.storage_object_key,
            )
            body = response["Body"]
            return FileDownload(
                chunks=self._iter_streaming_body(body),
                content_type=response.get("ContentType") or exame.storage_content_type or "application/pdf",
                size_bytes=response.get("ContentLength") or exame.storage_size_bytes,
                original_filename=exame.original_filename,
            )

        if provider == "local" and exame.storage_object_key:
            return FileDownload(
                chunks=self._iter_local_file(exame.storage_object_key),
                content_type=exame.storage_content_type or "application/pdf",
                size_bytes=exame.storage_size_bytes,
                original_filename=exame.original_filename,
            )

        raise FileNotFoundError("Arquivo persistido do exame nao encontrado")

    @contextmanager
    def materialize_to_temp_path(self, exame: Any) -> Generator[str, None, None]:
        legacy_path = self._resolve_legacy_local_path(exame)
        if legacy_path:
            yield legacy_path
            return

        if (exame.storage_provider or "").lower() == "local" and exame.storage_object_key:
            yield exame.storage_object_key
            return

        download = self.stream_file(exame)
        suffix = os.path.splitext(exame.original_filename or exame.storage_object_key or "exame.pdf")[1] or ".pdf"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            with temp_file as handle:
                for chunk in download.chunks:
                    handle.write(chunk)
            yield temp_file.name
        finally:
            try:
                os.remove(temp_file.name)
            except OSError as exc:
                logger.warning(
                    "Falha ao remover arquivo temporario materializado %s: %s",
                    temp_file.name,
                    exc,
                )

    def _store_file_local(
        self,
        *,
        source_path: str,
        object_key: str,
        content_type: str,
        checksum: str,
        size_bytes: int,
    ) -> StoredFileMetadata:
        destination = os.path.join(self.local_storage_dir, object_key)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(source_path, destination)
        return StoredFileMetadata(
            storage_provider="local",
            storage_bucket=None,
            storage_object_key=destination,
            storage_content_type=content_type,
            storage_size_bytes=size_bytes,
            storage_checksum=checksum,
            storage_status="stored",
            url_documento=f"local://{object_key}",
        )

    def _store_file_s3(
        self,
        *,
        source_path: str,
        object_key: str,
        content_type: str,
        checksum: str,
        size_bytes: int,
    ) -> StoredFileMetadata:
        try:
            client = self._get_s3_client()
            self._ensure_bucket_exists(client)
            with open(source_path, "rb") as file_handle:
                client.upload_fileobj(
                    file_handle,
                    self.bucket,
                    object_key,
                    ExtraArgs={"ContentType": content_type},
                )
        except OSError as exc:
            raise StorageUnavailableError("Falha ao salvar arquivo no storage S3-compatible") from exc

        return StoredFileMetadata(
            storage_provider="s3",
            storage_bucket=self.bucket,
            storage_object_key=object_key,
            storage_content_type=content_type,
            storage_size_bytes=size_bytes,
            storage_checksum=checksum,
            storage_status="stored",
            url_documento=f"s3://{self.bucket}/{object_key}",
        )

    def _get_s3_client(self):
        try:
            import boto3
            from botocore.client import Config
        except ImportError as exc:
            raise StorageUnavailableError("Dependencias S3 ausentes no ambiente atual") from exc

        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.OCR_STORAGE_ENDPOINT,
                aws_access_key_id=settings.OCR_STORAGE_ACCESS_KEY,
                aws_secret_access_key=settings.OCR_STORAGE_SECRET_KEY,
                region_name=settings.OCR_STORAGE_REGION,
                config=Config(
                    s3={"addressing_style": "path" if settings.OCR_STORAGE_FORCE_PATH_STYLE else "virtual"}
                ),
            )
        return self._s3_client

    def _ensure_bucket_exists(self, client) -> None:
        try:
            client.head_bucket(Bucket=self.bucket)
        except Exception as exc:
            error_code = None
            response = getattr(exc, "response", None)
            if isinstance(response, dict):
                error_code = str(response.get("Error", {}).get("Code", ""))

            missing_bucket_codes = {"404", "NoSuchBucket", "NotFound", "NoSuchBucketPolicy"}
            if error_code in missing_bucket_codes:
                client.create_bucket(Bucket=self.bucket)
                return

            raise StorageUnavailableError(
                f"Falha ao validar bucket S3 '{self.bucket}': {exc}"
            ) from exc

    def _calculate_checksum(self, source_path: str) -> str:
        digest = hashlib.sha256()
        with open(source_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _resolve_legacy_local_path(self, exame: Any) -> Optional[str]:
        if exame.storage_object_key or exame.storage_provider:
            return None
        if exame.url_documento and os.path.exists(exame.url_documento):
            return exame.url_documento
        return None

    def _iter_local_file(self, path: str) -> Iterator[bytes]:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                yield chunk

    def _iter_streaming_body(self, body) -> Iterator[bytes]:
        try:
            while True:
                chunk = body.read(8192)
                if not chunk:
                    break
                yield chunk
        finally:
            try:
                body.close()
            except Exception as exc:
                logger.warning("Falha ao fechar body de streaming S3: %s", exc)
