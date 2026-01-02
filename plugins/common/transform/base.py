class FileTransform:
    def apply(self, data: bytes) -> bytes:
        return data

class IdentityTransform(FileTransform):
    """Default no-op transform"""
    pass
