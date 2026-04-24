# File Management System Design

## Overview

The file management system provides a unified interface for storing, retrieving, and managing uploaded files in the administration application. The system abstracts underlying storage mechanisms (database, filesystem, S3) behind a virtual file manager interface, allowing files to be managed independently of their actual storage location.

---

## Core Principles

1. **Abstraction Over Implementation:** Virtual file managers define an interface; concrete implementations handle storage specifics.
2. **Path Security:** File paths are never directly exposed to users. All file access goes through the file manager's retrieval interface, ensuring paths follow the `userid/uuid` pattern securely.
3. **Lazy Loading:** File data is loaded on-demand rather than cached in memory, minimizing overhead.
4. **Audit Trail:** All file operations preserve `created_by`, `updated_by`, `created_at`, and `updated_at` metadata.
5. **Storage Agnostic:** The control layer does not know or care which storage backend is active; swapping backends is a configuration change, not a code change.

---

## Data Model Layer (`models/`)

### UploadedFile Model

The `UploadedFile` model stores metadata about uploaded files and acts as the single source of truth for file information across the system.

**Purpose:** Persist file metadata and determine which storage backend currently holds the file data.

**Location:** `app/administration/models/file.py`

**Schema:**

```python
class UploadedFile(models.Model):
    """
    Metadata record for uploaded files stored in one of multiple backends.
    
    The model tracks filename, size, mime type, and storage backend information.
    Actual file data is managed by the appropriate virtual file manager
    based on the storage_backend value.
    """
    
    # Core identity and metadata
    id = models.BigAutoField(primary_key=True)
    filename = models.CharField(max_length=255)  # Original filename
    file_size = models.BigIntegerField()  # Size in bytes
    mime_type = models.CharField(max_length=100)  # RFC 2045 MIME type
    description = models.TextField(blank=True)  # Optional user description
    
    # Storage backend identification
    storage_backend = models.CharField(
        max_length=20,
        choices=[
            ('database', 'Database (BLOB)'),
            ('filesystem', 'Filesystem (Local OS)'),
            ('s3', 'S3-compatible object storage'),
        ],
        default='database'
    )
    
    # Storage location hint (used by some backends)
    # Format: 'userid/uuid' — never exposed directly to users
    storage_path_hint = models.CharField(max_length=500, blank=True)
    
    # Audit trail (standard per project)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='files_created')
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='files_updated')
    
    # Optional metadata
    tags = models.JSONField(default=list, blank=True)  # For categorization
    is_technical_library = models.BooleanField(default=False)
    
    # Constants
    STORAGE_THRESHOLD = 1024 * 1024  # 1MB: switch to filesystem for large files
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB maximum file size
    
    ALLOWED_EXTENSION_GROUPS = {
        'images': {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'},
        'documents': {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'},
        'archives': {'.zip', '.tar', '.gz', '.7z'},
        'data': {'.csv', '.json', '.xml', '.txt', '.log'},
    }
```

**Responsibilities:**
- Store file metadata (name, size, type, description).
- Track which storage backend holds the actual file.
- Maintain audit trail for compliance and debugging.
- Validate file extensions and sizes.

**No Business Logic:** The model does not handle uploads, retrievals, or deletions directly. All file I/O is orchestrated through the control layer and virtual file managers.

---

## Control Layer

### 1. Domain Struct: `FileStruct`

**Location:** `app/administration/control_layer/domain_structs/file_struct.py`

**Purpose:** Represent a file and its metadata as an immutable, serializable aggregate for use in presentation and control layers.

```python
@dataclass
class FileStruct:
    """
    Immutable representation of a file record for display and manipulation.
    
    Provides:
    - Safe metadata for templates and APIs.
    - Lazy loaders for file data (loaded on-demand).
    - Structured access to file properties (size, extension, MIME type).
    """
    
    id: int
    filename: str
    file_size: int  # Bytes
    mime_type: str
    storage_backend: str
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    description: str = ""
    tags: list = field(default_factory=list)
    is_technical_library: bool = False
    
    def to_dict(self) -> dict:
        """
        Serialize to template-safe dictionary.
        Never includes raw storage paths or raw file data.
        """
        return {
            'id': self.id,
            'filename': self.filename,
            'file_size': self.file_size,
            'file_size_display': self.get_file_size_display(),
            'mime_type': self.mime_type,
            'storage_backend': self.storage_backend,
            'description': self.description,
            'tags': self.tags,
            'is_technical_library': self.is_technical_library,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by_id': self.created_by_id,
            'icon_class': self.get_icon_class(),
        }
    
    def get_file_size_display(self) -> str:
        """Return human-readable file size (e.g., '2.5 MB')."""
        pass
    
    def get_icon_class(self) -> str:
        """Return Bulma/Bootstrap icon class for file type."""
        pass
    
    def get_extension(self) -> str:
        """Return lowercase file extension (e.g., '.pdf')."""
        pass
    
    def is_image(self) -> bool:
        """True if file is in the images extension group."""
        pass
```

### 2. Virtual File Manager Interface

**Location:** `app/administration/control_layer/file_manager.py`

**Purpose:** Define the contract that all file storage backends must implement.

```python
from abc import ABC, abstractmethod

class VirtualFileManager(ABC):
    """
    Abstract base class defining the interface for file storage backends.
    
    Concrete implementations:
    - DatabaseFileManager: stores file data as BLOB in UploadedFile record
    - FilesystemFileManager: stores file data on local OS filesystem
    - S3FileManager: stores file data in S3-compatible object storage
    
    Key principle: All methods operate on UploadedFile metadata records;
    the manager is responsible for persisting actual data to its backend.
    """
    
    @abstractmethod
    def save(self, uploaded_file: UploadedFile, file_data: bytes) -> FileStruct:
        """
        Persist file data to this backend.
        
        Args:
            uploaded_file: UploadedFile model instance (may be unsaved).
            file_data: Raw file bytes to persist.
        
        Returns:
            FileStruct wrapping the now-persisted file metadata.
        
        Raises:
            FileSizeError: if file_data exceeds MAX_FILE_SIZE.
            FileStorageError: if backend write fails.
        """
        pass
    
    @abstractmethod
    def retrieve(self, uploaded_file: UploadedFile) -> bytes:
        """
        Load file data from this backend.
        
        Args:
            uploaded_file: UploadedFile model instance to retrieve.
        
        Returns:
            Raw file bytes.
        
        Raises:
            FileNotFoundError: if file data no longer exists on backend.
            FileStorageError: if backend read fails.
        """
        pass
    
    @abstractmethod
    def delete(self, uploaded_file: UploadedFile) -> None:
        """
        Remove file data from this backend.
        
        Args:
            uploaded_file: UploadedFile model instance to delete.
        
        Raises:
            FileNotFoundError: if file already deleted or never existed.
            FileStorageError: if backend delete fails.
        
        Note:
            The UploadedFile model record itself is not deleted;
            only the actual file data is removed.
        """
        pass
    
    @abstractmethod
    def exists(self, uploaded_file: UploadedFile) -> bool:
        """
        Check whether file data exists on this backend.
        
        Args:
            uploaded_file: UploadedFile model instance to check.
        
        Returns:
            True if file data can be retrieved; False otherwise.
        """
        pass
```

### 3. Concrete File Manager Implementations

#### A. DatabaseFileManager

**Location:** `app/administration/control_layer/database_file_manager.py`

**Purpose:** Store small files as BLOB data directly in the UploadedFile model's `file_data` field.

**Typical use case:** Files ≤ 1MB; small PDFs, images, configuration files.

```python
class DatabaseFileManager(VirtualFileManager):
    """
    Stores file data as binary BLOB in the UploadedFile model record.
    
    Suitable for:
    - Small files (< 1MB).
    - Files that must be transactionally consistent with metadata.
    - Development environments with no external storage.
    
    Trade-offs:
    - Database size grows with each file.
    - Query performance may degrade with large BLOB fields.
    - Not suitable for streaming or partial reads.
    """
    
    def save(self, uploaded_file: UploadedFile, file_data: bytes) -> FileStruct:
        """Store file data as BLOB in the model."""
        # Validate file size
        if len(file_data) > UploadedFile.MAX_FILE_SIZE:
            raise FileSizeExceededError(...)
        
        # Store data and backend type
        uploaded_file.file_data = file_data
        uploaded_file.storage_backend = 'database'
        uploaded_file.storage_path_hint = ""
        uploaded_file.save()
        
        return self._struct_from_model(uploaded_file)
    
    def retrieve(self, uploaded_file: UploadedFile) -> bytes:
        """Retrieve file data from BLOB field."""
        if uploaded_file.file_data is None:
            raise FileNotFoundError(f"File {uploaded_file.id} has no data in database.")
        return uploaded_file.file_data
    
    def delete(self, uploaded_file: UploadedFile) -> None:
        """Clear BLOB field (does not delete the model record)."""
        uploaded_file.file_data = None
        uploaded_file.save()
    
    def exists(self, uploaded_file: UploadedFile) -> bool:
        """Check whether BLOB data is present."""
        return uploaded_file.file_data is not None
```

#### B. FilesystemFileManager

**Location:** `app/administration/control_layer/filesystem_file_manager.py`

**Purpose:** Store files on the local operating system filesystem using a secure path hierarchy.

**Typical use case:** Files > 1MB; large PDFs, video files, bulk exports.

**Path structure:** Files are stored at:
```
<UPLOAD_ROOT>/<user_id>/<uuid4>/filename
```

This ensures:
- Files are grouped by user for easy per-user cleanup.
- UUIDs prevent filename collisions and path traversal attacks.
- The actual path is never exposed; only the file ID is used for retrieval.

```python
class FilesystemFileManager(VirtualFileManager):
    """
    Stores file data on the local filesystem using secure path hierarchy.
    
    Path format: <UPLOAD_ROOT>/<user_id>/<uuid4>/filename
    
    Suitable for:
    - Large files (> 1MB).
    - Production systems with local or network storage.
    - High-throughput file operations.
    
    Trade-offs:
    - Requires filesystem access and permissions.
    - Must handle concurrent access carefully.
    - Backup and disaster recovery are filesystem-level concerns.
    """
    
    UPLOAD_ROOT = settings.UPLOAD_ROOT  # e.g., 'uploads/'
    
    def save(self, uploaded_file: UploadedFile, file_data: bytes, user_id: int) -> FileStruct:
        """
        Store file data in filesystem hierarchy.
        
        Args:
            uploaded_file: UploadedFile model instance.
            file_data: Raw file bytes.
            user_id: ID of uploading user (for path hierarchy).
        
        Returns:
            FileStruct wrapping the persisted file.
        """
        # Validate file size
        if len(file_data) > UploadedFile.MAX_FILE_SIZE:
            raise FileSizeExceededError(...)
        
        # Generate secure path
        storage_uuid = uuid.uuid4()
        safe_filename = secure_filename(uploaded_file.filename)
        file_path = self._construct_path(user_id, storage_uuid, safe_filename)
        
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file atomically
        file_path.write_bytes(file_data)
        
        # Update metadata
        uploaded_file.storage_backend = 'filesystem'
        uploaded_file.storage_path_hint = f"{user_id}/{storage_uuid}"
        uploaded_file.save()
        
        return self._struct_from_model(uploaded_file)
    
    def retrieve(self, uploaded_file: UploadedFile) -> bytes:
        """Load file data from filesystem."""
        file_path = self._resolve_path(uploaded_file)
        if not file_path.exists():
            raise FileNotFoundError(f"File {uploaded_file.id} not found on filesystem.")
        return file_path.read_bytes()
    
    def delete(self, uploaded_file: UploadedFile) -> None:
        """Remove file from filesystem and clean up empty directories."""
        file_path = self._resolve_path(uploaded_file)
        if file_path.exists():
            file_path.unlink()
        
        # Attempt to remove empty parent directories (user/uuid)
        try:
            if not any(file_path.parent.iterdir()):
                file_path.parent.rmdir()
        except OSError:
            pass  # Directory not empty or permission denied; ignore
    
    def exists(self, uploaded_file: UploadedFile) -> bool:
        """Check whether file exists on filesystem."""
        try:
            file_path = self._resolve_path(uploaded_file)
            return file_path.exists()
        except Exception:
            return False
    
    def _construct_path(self, user_id: int, storage_uuid: uuid.UUID, filename: str) -> Path:
        """Build secure path: <UPLOAD_ROOT>/<user_id>/<uuid4>/filename"""
        return Path(self.UPLOAD_ROOT) / str(user_id) / str(storage_uuid) / filename
    
    def _resolve_path(self, uploaded_file: UploadedFile) -> Path:
        """
        Reconstruct filesystem path from stored hint.
        
        Ensures path stays within UPLOAD_ROOT and cannot be manipulated.
        """
        hint = uploaded_file.storage_path_hint  # 'user_id/uuid4'
        filename = uploaded_file.filename
        
        # Validate path segments are not manipulated
        parts = hint.split('/')
        if len(parts) != 2 or '..' in hint:
            raise ValueError(f"Invalid storage path hint: {hint}")
        
        return Path(self.UPLOAD_ROOT) / hint / filename
```

#### C. S3FileManager

**Location:** `app/administration/control_layer/s3_file_manager.py`

**Purpose:** Store files in S3-compatible object storage (AWS S3, Minio, etc.).

**Typical use case:** Cloud deployments, high-availability setups, unlimited storage.

**Path structure:** Objects are stored at:
```
s3://<bucket>/<user_id>/<uuid4>/filename
```

```python
class S3FileManager(VirtualFileManager):
    """
    Stores file data in S3-compatible object storage.
    
    Object key format: <user_id>/<uuid4>/filename
    
    Suitable for:
    - Cloud deployments (AWS S3, Minio, DigitalOcean Spaces, etc.).
    - High-availability requirements.
    - Unlimited storage capacity.
    - Integration with CDN/CloudFront.
    
    Trade-offs:
    - Requires S3 credentials and network access.
    - Costs per API call and data transfer.
    - Eventual consistency (read-after-write may not be immediate).
    """
    
    def __init__(self, s3_client, bucket_name: str):
        """
        Initialize S3 manager.
        
        Args:
            s3_client: boto3 S3 client.
            bucket_name: S3 bucket name for file storage.
        """
        self.s3_client = s3_client
        self.bucket_name = bucket_name
    
    def save(self, uploaded_file: UploadedFile, file_data: bytes, user_id: int) -> FileStruct:
        """
        Upload file data to S3.
        
        Args:
            uploaded_file: UploadedFile model instance.
            file_data: Raw file bytes.
            user_id: ID of uploading user (for object key hierarchy).
        
        Returns:
            FileStruct wrapping the persisted file.
        """
        # Validate file size
        if len(file_data) > UploadedFile.MAX_FILE_SIZE:
            raise FileSizeExceededError(...)
        
        # Generate object key
        storage_uuid = uuid.uuid4()
        safe_filename = secure_filename(uploaded_file.filename)
        object_key = f"{user_id}/{storage_uuid}/{safe_filename}"
        
        # Upload to S3
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_data,
                ContentType=uploaded_file.mime_type,
                Metadata={
                    'original_filename': uploaded_file.filename,
                    'uploaded_by': str(user_id),
                }
            )
        except ClientError as e:
            raise FileStorageError(f"S3 upload failed: {e}")
        
        # Update metadata
        uploaded_file.storage_backend = 's3'
        uploaded_file.storage_path_hint = f"{user_id}/{storage_uuid}"
        uploaded_file.save()
        
        return self._struct_from_model(uploaded_file)
    
    def retrieve(self, uploaded_file: UploadedFile) -> bytes:
        """Download file data from S3."""
        object_key = self._construct_object_key(uploaded_file)
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File {uploaded_file.id} not found in S3.")
            raise FileStorageError(f"S3 download failed: {e}")
    
    def delete(self, uploaded_file: UploadedFile) -> None:
        """Delete file data from S3."""
        object_key = self._construct_object_key(uploaded_file)
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
        except ClientError as e:
            raise FileStorageError(f"S3 delete failed: {e}")
    
    def exists(self, uploaded_file: UploadedFile) -> bool:
        """Check whether file exists in S3."""
        object_key = self._construct_object_key(uploaded_file)
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def _construct_object_key(self, uploaded_file: UploadedFile) -> str:
        """Build S3 object key: <user_id>/<uuid4>/filename"""
        hint = uploaded_file.storage_path_hint  # 'user_id/uuid4'
        return f"{hint}/{uploaded_file.filename}"
```

### 4. FileContext

**Location:** `app/administration/control_layer/file_context.py`

**Purpose:** Orchestrate all file operations (upload, retrieve, delete) by delegating to the appropriate virtual file manager based on configuration.

**Key responsibility:** Determine which backend to use for a given operation and coordinate between the file manager interface and the UploadedFile model.

```python
class FileContext:
    """
    Central orchestrator for file upload, retrieval, and deletion.
    
    Routes all file operations to the appropriate storage backend based on
    configuration. Provides a unified API for the presentation layer regardless
    of which backend is active.
    """
    
    def __init__(self, file_manager: VirtualFileManager):
        """
        Initialize with a specific file manager.
        
        Args:
            file_manager: Instance of VirtualFileManager (e.g., DatabaseFileManager).
        """
        self.file_manager = file_manager
    
    def upload_file(
        self,
        filename: str,
        file_data: bytes,
        mime_type: str,
        created_by: User,
        description: str = "",
        tags: list = None,
        is_technical_library: bool = False,
    ) -> FileStruct:
        """
        Upload a file and store metadata.
        
        Args:
            filename: Original filename from user.
            file_data: Raw file bytes.
            mime_type: RFC 2045 MIME type.
            created_by: User performing the upload.
            description: Optional description.
            tags: Optional list of tags for categorization.
            is_technical_library: Whether file is part of technical library.
        
        Returns:
            FileStruct wrapping the newly uploaded file.
        
        Raises:
            FileSizeExceededError: if file_data exceeds MAX_FILE_SIZE.
            InvalidFileTypeError: if file extension not allowed.
            FileStorageError: if backend write fails.
        """
        # Validate extension
        self._validate_file_extension(filename)
        
        # Validate size
        if len(file_data) > UploadedFile.MAX_FILE_SIZE:
            raise FileSizeExceededError(
                f"File exceeds maximum size of {UploadedFile.MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # Create model instance
        uploaded_file = UploadedFile(
            filename=filename,
            file_size=len(file_data),
            mime_type=mime_type,
            created_by=created_by,
            updated_by=created_by,
            description=description,
            tags=tags or [],
            is_technical_library=is_technical_library,
        )
        
        # Delegate to file manager
        file_struct = self.file_manager.save(uploaded_file, file_data, user_id=created_by.id)
        
        return file_struct
    
    def download_file(self, file_id: int) -> tuple[FileStruct, bytes]:
        """
        Retrieve a file's metadata and data.
        
        Args:
            file_id: Primary key of the UploadedFile record.
        
        Returns:
            Tuple of (FileStruct, raw file bytes).
        
        Raises:
            UploadedFile.DoesNotExist: if file_id not found.
            FileNotFoundError: if file data no longer exists on backend.
            FileStorageError: if backend read fails.
        """
        uploaded_file = UploadedFile.objects.get(id=file_id)
        file_data = self.file_manager.retrieve(uploaded_file)
        file_struct = self._struct_from_model(uploaded_file)
        return file_struct, file_data
    
    def delete_file(self, file_id: int) -> None:
        """
        Delete file data and its metadata record.
        
        Args:
            file_id: Primary key of the UploadedFile record.
        
        Raises:
            UploadedFile.DoesNotExist: if file_id not found.
            FileStorageError: if backend delete fails.
        
        Note:
            The UploadedFile model record is soft-deleted (marked inactive)
            rather than hard-deleted, preserving audit trail.
        """
        uploaded_file = UploadedFile.objects.get(id=file_id)
        
        # Delete file data from backend
        self.file_manager.delete(uploaded_file)
        
        # Soft-delete model (if soft-delete is implemented) or hard-delete
        # For now, hard delete; consider adding an is_deleted flag later
        uploaded_file.delete()
    
    def get_file_metadata(self, file_id: int) -> FileStruct:
        """
        Retrieve file metadata without loading file data.
        
        Args:
            file_id: Primary key of the UploadedFile record.
        
        Returns:
            FileStruct wrapping the file metadata.
        
        Raises:
            UploadedFile.DoesNotExist: if file_id not found.
        """
        uploaded_file = UploadedFile.objects.get(id=file_id)
        return self._struct_from_model(uploaded_file)
    
    def list_files(self, created_by: User = None, tags: list = None) -> list[FileStruct]:
        """
        List files with optional filtering.
        
        Args:
            created_by: Optional User to filter by creator.
            tags: Optional list of tags to filter by.
        
        Returns:
            List of FileStruct instances matching criteria.
        """
        queryset = UploadedFile.objects.all()
        
        if created_by:
            queryset = queryset.filter(created_by=created_by)
        
        if tags:
            queryset = queryset.filter(tags__overlap=tags)
        
        return [self._struct_from_model(uf) for uf in queryset]
    
    def _validate_file_extension(self, filename: str) -> None:
        """Ensure file extension is in allowed groups."""
        ext = Path(filename).suffix.lower()
        allowed = set()
        for group in UploadedFile.ALLOWED_EXTENSION_GROUPS.values():
            allowed.update(group)
        
        if ext not in allowed:
            raise InvalidFileTypeError(f"File extension '{ext}' is not allowed.")
    
    @staticmethod
    def _struct_from_model(uploaded_file: UploadedFile) -> FileStruct:
        """Convert UploadedFile model to FileStruct."""
        return FileStruct(
            id=uploaded_file.id,
            filename=uploaded_file.filename,
            file_size=uploaded_file.file_size,
            mime_type=uploaded_file.mime_type,
            storage_backend=uploaded_file.storage_backend,
            created_by_id=uploaded_file.created_by_id,
            created_at=uploaded_file.created_at,
            updated_at=uploaded_file.updated_at,
            description=uploaded_file.description,
            tags=uploaded_file.tags,
            is_technical_library=uploaded_file.is_technical_library,
        )
```

---

## Presentation Layer

### Entrypoints

**Location:** `app/administration/presentation_layer/entrypoints/file_management.py`

**Responsibilities:**
- Parse HTTP file uploads
- Delegate to FileContext
- Return file download responses
- Handle errors and edge cases

```python
def upload_file(request):
    """
    Handle file upload from form POST.
    
    Expects: multipart/form-data with:
    - file: file input
    - description: optional text description
    - tags: optional comma-separated tags
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    
    file_obj = request.FILES.get('file')
    if not file_obj:
        return JsonResponse({'error': 'No file provided'}, status=400)
    
    description = request.POST.get('description', '')
    tags = request.POST.get('tags', '').split(',') if request.POST.get('tags') else []
    
    try:
        file_data = file_obj.read()
        
        # Get file manager from app config (dependency injection)
        file_context = get_file_context()
        file_struct = file_context.upload_file(
            filename=file_obj.name,
            file_data=file_data,
            mime_type=file_obj.content_type,
            created_by=request.user,
            description=description,
            tags=tags,
        )
        
        return JsonResponse({
            'success': True,
            'file': file_struct.to_dict(),
        })
    
    except (FileSizeExceededError, InvalidFileTypeError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    except FileStorageError as e:
        return JsonResponse({'error': 'Storage error'}, status=500)


def download_file(request, file_id):
    """
    Download a file by its ID.
    
    Returns the file data with appropriate headers.
    """
    try:
        file_context = get_file_context()
        file_struct, file_data = file_context.download_file(file_id)
        
        response = HttpResponse(file_data, content_type=file_struct.mime_type)
        response['Content-Disposition'] = f'attachment; filename="{file_struct.filename}"'
        return response
    
    except UploadedFile.DoesNotExist:
        return HttpResponseNotFound('File not found')
    except FileNotFoundError:
        return HttpResponseNotFound('File data no longer available')
    except FileStorageError as e:
        return HttpResponse('Storage error', status=500)


def delete_file(request, file_id):
    """Delete a file by its ID (HTMX-compatible)."""
    if request.method != 'DELETE':
        return HttpResponseNotAllowed(['DELETE'])
    
    try:
        file_context = get_file_context()
        file_context.delete_file(file_id)
        return HttpResponse(status=204)
    
    except UploadedFile.DoesNotExist:
        return HttpResponseNotFound('File not found')
    except FileStorageError as e:
        return HttpResponse('Storage error', status=500)
```

### Search

**Location:** `app/administration/presentation_layer/search/file_search.py`

Encapsulates queries for listing and filtering files.

```python
def files_for_user(user: User, limit: int = 100) -> list[FileStruct]:
    """Retrieve all files created by a specific user."""
    file_context = get_file_context()
    return file_context.list_files(created_by=user)


def files_by_tag(tag: str, limit: int = 100) -> list[FileStruct]:
    """Retrieve all files tagged with a specific tag."""
    file_context = get_file_context()
    return file_context.list_files(tags=[tag])
```

---

## Exception Hierarchy

**Location:** `app/administration/control_layer/file_exceptions.py`

```python
class FileManagementError(Exception):
    """Base exception for all file management errors."""
    pass


class FileSizeExceededError(FileManagementError):
    """File exceeds maximum allowed size."""
    pass


class InvalidFileTypeError(FileManagementError):
    """File extension or MIME type is not allowed."""
    pass


class FileStorageError(FileManagementError):
    """Underlying storage backend failed (read, write, delete)."""
    pass
```

---

## Configuration and Dependency Injection

**Location:** `app/administration/apps.py`

```python
class AdministrationConfig(AppConfig):
    name = 'app.administration'
    
    def ready(self):
        # Initialize file context with appropriate backend
        from django.conf import settings
        
        backend_type = getattr(settings, 'FILE_STORAGE_BACKEND', 'database')
        
        if backend_type == 'database':
            file_manager = DatabaseFileManager()
        elif backend_type == 'filesystem':
            file_manager = FilesystemFileManager()
        elif backend_type == 's3':
            import boto3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            file_manager = S3FileManager(s3_client, settings.S3_BUCKET_NAME)
        else:
            raise ValueError(f"Unknown FILE_STORAGE_BACKEND: {backend_type}")
        
        # Store in app config for global access
        self.file_context = FileContext(file_manager)


def get_file_context() -> FileContext:
    """Retrieve the globally-configured FileContext."""
    from django.apps import apps
    return apps.get_app_config('administration').file_context
```

---

## Security Considerations

### 1. Path Traversal Prevention
- File paths use UUIDs and are never directly exposed.
- All path reconstruction validates path segments and rejects `..` or absolute paths.

### 2. File Type Validation
- Extensions are validated against a whitelist of allowed groups.
- MIME types are validated during upload.
- Never trust client-supplied MIME type; validate extension first.

### 3. File Size Limits
- Hard maximum of 100MB per file to prevent DoS.
- Storage threshold (1MB) automatic to optimize resource use.

### 4. Access Control
- Entrypoints must enforce authorization (e.g., via Django permissions or ownership checks).
- The file manager interface itself does not enforce permissions; that is the responsibility of the control layer and entrypoint.

### 5. Audit Trail
- All uploads and deletions are tracked via `created_by`, `updated_by`, `created_at`, `updated_at`.
- Consider adding a delete log if hard-delete is used instead of soft-delete.

---

## Testing Strategy

### Unit Tests

**File Manager Tests:** Test each concrete implementation (Database, Filesystem, S3) with:
- Successful save, retrieve, delete operations.
- Error cases (file not found, permission denied, size exceeded).
- Path construction and validation.

**FileContext Tests:** Test orchestration:
- Correct routing to underlying manager.
- Extension and size validation.
- Model creation and metadata handling.

### Integration Tests

- Upload → download → verify data integrity.
- Cross-backend consistency (upload to one backend, verify metadata).
- Permission checks at entrypoint level.

### End-to-End Tests

- HTML form upload via browser.
- HTMX delete with confirmation.
- Multiple files from same user.

---

## Migration Path

### Phase 1: Database Backend
- Start with `DatabaseFileManager` for all files.
- Simple; no external dependencies.

### Phase 2: Filesystem Backend
- Large files (> 1MB) automatically stored on filesystem.
- Update FileContext to choose backend based on file size.

### Phase 3: S3 Backend
- Production deployments use S3 with local fallback.
- Configuration-driven backend selection.

### Phase 4: Multi-Backend Support (Future)
- User/admin UI to configure upload target.
- Move existing files between backends.

---

## Summary

The file management system provides a **clean, composable architecture** that:

1. **Abstracts storage** behind a virtual file manager interface.
2. **Secures paths** using UUIDs and user IDs with no direct exposure.
3. **Follows project patterns** (Struct, Context, Manager, Guard, Adaptor).
4. **Maintains audit trail** via standard user/timestamp fields.
5. **Enables easy backend swapping** via configuration.
6. **Scales** from small (database) to large (S3) deployments.
