import enum


class FirmRole(str, enum.Enum):
    """A person's role inside an accounting / bookkeeping firm. It decides what
    they can do for the firm itself and, through the firm, in every client
    business the firm manages (see firms/application/access.py).
    """

    OWNER = "owner"
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class FirmStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class FirmMembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    REMOVED = "removed"
