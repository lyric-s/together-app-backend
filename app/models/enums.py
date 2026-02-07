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

class AIContentCategory(str, Enum):
    NORMAL_CONTENT = "NORMAL_CONTENT"           
    TOXIC_LANGUAGE = "TOXIC_LANGUAGE"           
    INAPPROPRIATE_CONTENT = "INAPPROPRIATE_CONTENT"  
    SPAM_LIKE = "SPAM_LIKE"                     
    FRAUD_SUSPECTED = "FRAUD_SUSPECTED"         
    MISLEADING_INFORMATION = "MISLEADING_INFORMATION" 
    OTHER = "OTHER"                            

class ContentType(str, Enum):
    """
    Specifies the type of content being moderated for the AI flagging system.
    """

    USER = "USER"
    MISSION = "MISSION"
