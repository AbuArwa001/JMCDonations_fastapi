"""
Role-Based Access Control (RBAC) permission catalog for the JMC Admin Portal.

Permissions are flat string keys in the form ``<module>.<action>``.
A role holding the wildcard ``*`` is treated as a Super Admin and is granted
every permission (including user & role management).
"""
from typing import Dict, List, TypedDict

WILDCARD = "*"
SUPER_ADMIN_ROLE = "Super Admin"


class PermissionDef(TypedDict):
    key: str
    label: str
    description: str
    group: str


PERMISSIONS: List[PermissionDef] = [
    # ---- Overview ----
    {"key": "dashboard.view", "label": "Executive Dashboard", "description": "View treasury analytics, trends and KPIs", "group": "Overview"},

    # ---- Finance & Donations ----
    {"key": "drives.view", "label": "View Donation Drives", "description": "Browse campaigns and their progress", "group": "Finance & Donations"},
    {"key": "drives.manage", "label": "Manage Donation Drives", "description": "Create, edit, close and delete campaigns", "group": "Finance & Donations"},
    {"key": "categories.manage", "label": "Manage Categories", "description": "Create, edit and delete donation categories", "group": "Finance & Donations"},
    {"key": "donations.view", "label": "View Donations Log", "description": "View transactions, pending cash and exports", "group": "Finance & Donations"},
    {"key": "donations.manage", "label": "Manage Donations", "description": "Verify cash, update transaction status", "group": "Finance & Donations"},
    {"key": "accounts.view", "label": "View Bank Accounts", "description": "View mosque settlement accounts", "group": "Finance & Donations"},
    {"key": "accounts.manage", "label": "Manage Bank Accounts", "description": "Add, edit and remove settlement accounts", "group": "Finance & Donations"},
    {"key": "transfers.view", "label": "View Transfers", "description": "View internal transfer history", "group": "Finance & Donations"},
    {"key": "transfers.manage", "label": "Initiate Transfers", "description": "Move funds between accounts", "group": "Finance & Donations"},

    # ---- Community & Content ----
    {"key": "darsas.manage", "label": "Darsas & Classes", "description": "Publish and manage darsas", "group": "Community & Content"},
    {"key": "inspiration.manage", "label": "Inspiration Quotes", "description": "Publish daily inspiration", "group": "Community & Content"},
    {"key": "khutba.manage", "label": "Friday Khutba", "description": "Publish khutba and send notifications", "group": "Community & Content"},
    {"key": "bulletins.manage", "label": "Friday Bulletins", "description": "Upload bulletins and notify the community", "group": "Community & Content"},
    {"key": "events.manage", "label": "Events", "description": "Create events, galleries and notify attendees", "group": "Community & Content"},
    {"key": "duas.manage", "label": "Duas", "description": "Curate dua categories and entries", "group": "Community & Content"},
    {"key": "quran.manage", "label": "Quran", "description": "Manage reciters and surah audio", "group": "Community & Content"},
    {"key": "prayer_times.manage", "label": "Prayer Timings", "description": "Cities, overrides and calculation settings", "group": "Community & Content"},
    {"key": "zakat.manage", "label": "Zakat Calculator", "description": "Maintain nisab rates", "group": "Community & Content"},

    # ---- System & Administration ----
    {"key": "features.manage", "label": "Feature Toggles", "description": "Enable or disable app features", "group": "System & Administration"},
    {"key": "users.manage", "label": "Manage Staff Users", "description": "Invite staff, assign roles, revoke access", "group": "System & Administration"},
    {"key": "roles.manage", "label": "Manage Roles", "description": "Create and edit roles & permissions", "group": "System & Administration"},
]

PERMISSION_KEYS = {p["key"] for p in PERMISSIONS}

COMMUNITY_PERMS = [
    "darsas.manage", "inspiration.manage", "khutba.manage", "bulletins.manage",
    "events.manage", "duas.manage", "quran.manage", "prayer_times.manage", "zakat.manage",
]

DEFAULT_ROLES: List[Dict] = [
    {
        "role_name": SUPER_ADMIN_ROLE,
        "description": "Unrestricted access to every module, including staff and role management.",
        "permissions": [WILDCARD],
        "color": "#c99335",
        "is_system": True,
    },
    {
        "role_name": "Finance Manager",
        "description": "Owns the treasury: drives, donations, bank accounts and transfers.",
        "permissions": [
            "dashboard.view", "drives.view", "drives.manage", "categories.manage",
            "donations.view", "donations.manage", "accounts.view", "accounts.manage",
            "transfers.view", "transfers.manage",
        ],
        "color": "#10b981",
        "is_system": False,
    },
    {
        "role_name": "Content Manager",
        "description": "Publishes community content: darsas, khutba, bulletins, events and more.",
        "permissions": list(COMMUNITY_PERMS),
        "color": "#0ea5e9",
        "is_system": False,
    },
    {
        "role_name": "Auditor",
        "description": "Read-only oversight of finances for accountability and reporting.",
        "permissions": ["dashboard.view", "drives.view", "donations.view", "accounts.view", "transfers.view"],
        "color": "#8b5cf6",
        "is_system": False,
    },
]


def sanitize_permissions(perms: List[str]) -> List[str]:
    """Drop unknown keys and de-duplicate while preserving order."""
    seen, out = set(), []
    for p in perms or []:
        if (p in PERMISSION_KEYS or p == WILDCARD) and p not in seen:
            seen.add(p)
            out.append(p)
    return out
