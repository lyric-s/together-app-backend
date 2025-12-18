from enum import Enum


class UserType(str, Enum):
    ADMIN = "admin"
    VOLUNTEER = "volunteer"
    ASSOCIATION = "association"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
