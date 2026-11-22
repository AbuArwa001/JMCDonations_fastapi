from typing import List, TypedDict

WILDCARD = "*"
SUPER_ADMIN_ROLE = "Super Admin"

class PermissionDef(TypedDict):
    key: str
    label: str
    description: str
    group: str

PERMISSIONS: List[PermissionDef] = [
    {"key": "dashboard.view", "label": "Executive Dashboard", "description": "View analytics and KPIs", "group": "Overview"},
    {"key": "drives.view", "label": "View Donation Drives", "description": "Browse campaigns and progress", "group": "Finance & Donations"},
    {"key": "drives.manage", "label": "Manage Donation Drives", "description": "Create, edit, close campaigns", "group": "Finance & Donations"},
    {"key": "categories.manage", "label": "Manage Categories", "description": "Manage donation categories", "group": "Finance & Donations"},
    {"key": "donations.view", "label": "View Donations Log", "description": "View transactions and exports", "group": "Finance & Donations"},
    {"key": "donations.manage", "label": "Manage Donations", "description": "Verify cash and update status", "group": "Finance & Donations"},
    {"key": "donations.delete", "label": "Delete Transactions", "description": "Delete records (Super Admin)", "group": "Finance & Donations"},
    {"key": "accounts.view", "label": "View Bank Accounts", "description": "View mosque settlement accounts", "group": "Finance & Donations"},
    {"key": "accounts.manage", "label": "Manage Bank Accounts", "description": "Add, edit, remove accounts", "group": "Finance & Donations"},
    {"key": "transfers.view", "label": "View Transfers", "description": "View transfer history", "group": "Finance & Donations"},
    {"key": "transfers.manage", "label": "Initiate Transfers", "description": "Move funds between accounts", "group": "Finance & Donations"},
    {"key": "darsas.manage", "label": "Darsas & Classes", "description": "Publish and manage darsas", "group": "Community & Content"},
    {"key": "inspiration.manage", "label": "Inspiration Quotes", "description": "Publish daily inspiration", "group": "Community & Content"},
    {"key": "khutba.manage", "label": "Friday Khutba", "description": "Publish khutba and notify", "group": "Community & Content"},
    {"key": "bulletins.manage", "label": "Friday Bulletins", "description": "Upload bulletins and notify", "group": "Community & Content"},
    {"key": "events.manage", "label": "Events", "description": "Create events and notify", "group": "Community & Content"},
    {"key": "duas.manage", "label": "Duas", "description": "Curate dua categories and entries", "group": "Community & Content"},
    {"key": "quran.manage", "label": "Quran", "description": "Manage reciters and surahs", "group": "Community & Content"},
    {"key": "prayer_times.manage", "label": "Prayer Timings", "description": "Overrides and settings", "group": "Community & Content"},
    {"key": "zakat.manage", "label": "Zakat Calculator", "description": "Maintain nisab rates", "group": "Community & Content"},
    {"key": "features.manage", "label": "Feature Toggles", "description": "Toggle app features", "group": "System & Administration"},
    {"key": "users.manage", "label": "Manage Staff Users", "description": "Invite staff and assign roles", "group": "System & Administration"},
    {"key": "roles.manage", "label": "Manage Roles", "description": "Create and edit roles", "group": "System & Administration"},
]

PERMISSION_KEYS = {p["key"] for p in PERMISSIONS}
COMMUNITY_PERMS = [
    "darsas.manage", "inspiration.manage", "khutba.manage", "bulletins.manage",
    "events.manage", "duas.manage", "quran.manage", "prayer_times.manage", "zakat.manage",
]

DEFAULT_ROLES = [
    {"role_name": SUPER_ADMIN_ROLE, "description": "Unrestricted access", "permissions": [WILDCARD], "color": "#c99335", "is_system": True},
    {"role_name": "Finance Manager", "description": "Treasury and donation operations", "permissions": ["dashboard.view", "drives.view", "drives.manage", "categories.manage", "donations.view", "donations.manage", "accounts.view", "accounts.manage", "transfers.view", "transfers.manage"], "color": "#10b981", "is_system": False},
    {"role_name": "Content Manager", "description": "Community content management", "permissions": list(COMMUNITY_PERMS), "color": "#0ea5e9", "is_system": False},
    {"role_name": "Auditor", "description": "Read-only financial oversight", "permissions": ["dashboard.view", "drives.view", "donations.view", "accounts.view", "transfers.view"], "color": "#8b5cf6", "is_system": False},
]

def sanitize_permissions(perms: List[str]) -> List[str]:
    seen, out = set(), []
    for p in perms or []:
        if (p in PERMISSION_KEYS or p == WILDCARD) and p not in seen:
            seen.add(p)
            out.append(p)
    return out
