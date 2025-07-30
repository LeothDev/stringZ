from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import pandas as pd


class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class IssueType(Enum):
    TOKEN_MISMATCH = "token_mismatch"
    FORMATTING_ERROR = "formatting_error"
    MISSING_TRANSLATION = "missing_translation"
    DUPLICATE_ENTRY = "duplicate_entry"


    
