# Standard Library
from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class OpeningHours:
    mondayHours: str = ""
    tuesdayHours: str = ""
    wednesdayHours: str = ""
    thursdayHours: str = ""
    fridayHours: str = ""
    saturdayHours: str = ""
    sundayHours: str = ""


@dataclass
class StoreData:
    store_id: str
    createdAt: datetime
    updatedAt: datetime
    name: str
    address: str
    phoneNumber: str
    website: str = ""
    openingHours: OpeningHours = field(default_factory=OpeningHours)
    imageUrls: List[str] = field(default_factory=list)
