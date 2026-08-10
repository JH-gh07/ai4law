from enum import Enum


class AssessmentTaskState(str, Enum):
    CREATED = "CREATED"
    PARSING = "PARSING"
    RETRIEVING = "RETRIEVING"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PATH_MISMATCH = "PATH_MISMATCH"


class PathMismatchError(ValueError):
    """Raised when diagnosis path does not match the requested report path,
    and the caller has opted into block_on_mismatch mode.
    """
