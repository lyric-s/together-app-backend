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
    HARASSMENT = "harassment"
    INAPPROPRIATE_BEHAVIOR = "inappropriate_behavior"
    SPAM = "spam"
    FRAUD = "fraud"
    OTHER = "other"


class ReportTarget(str, Enum):
    PROFILE = "profile"
    MESSAGE = "message"
    MISSION = "mission"
    OTHER = "other"
