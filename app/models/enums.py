from enum import Enum


class UserType(str, Enum):
    ADMIN = "admin"
    VOLUNTEER = "volunteer"
    ASSOCIATION = "association"


class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


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
