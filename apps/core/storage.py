import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage

class PrivateFileSystemStorage(FileSystemStorage):
    """
    Storage backend for confidential files that must NOT be exposed
    directly through static/media web servers.
    Files are stored in PRIVATE_STORAGE_ROOT and served exclusively
    through authenticated, permission-checked Django views.
    """
    def __init__(self, *args, **kwargs):
        kwargs['location'] = str(getattr(settings, 'PRIVATE_STORAGE_ROOT', settings.BASE_DIR / 'private_storage'))
        super().__init__(*args, **kwargs)

private_storage = PrivateFileSystemStorage()
