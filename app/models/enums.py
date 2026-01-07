from enum import Enum


class UserType(str, Enum):
    ADMIN = "admin"
    VOLUNTEER = "volunteer"
    ASSOCIATION = "association"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReportType(str, Enum):
    HARASSMENT = "HARASSMENT"
    INAPPROPRIATE_BEHAVIOR = "INAPPROPRIATE_BEHAVIOR"
    SPAM = "SPAM"
    FRAUD = "FRAUD"
    OTHER = "OTHER"


class ReportTarget(str, Enum):
    PROFILE = "PROFILE"
    MESSAGE = "MESSAGE"
    MISSION = "MISSION"
    OTHER = "OTHER"
