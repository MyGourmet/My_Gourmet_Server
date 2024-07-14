# Standard Library
from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class StoreData:
    store_id: str
    createdAt: datetime
    updatedAt: datetime
    name: str
    address: str
    city: str
    prefecture: str
    country: str
    phoneNumber: str
    website: str = ""
    openingHours: dict = field(default_factory=dict)
    imageUrls: List[str] = field(default_factory=list)
