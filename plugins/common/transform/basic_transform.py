from common.transform.base import FileTransform

class AddDotTransform(FileTransform):
    """
    Append a dot (.) to the end of each chunk.
    """
    def apply(self, data: bytes) -> bytes:
        return data + b"."
