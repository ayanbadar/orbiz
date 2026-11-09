"""
Single source of truth for store-level permissions.

A permission code is "<resource>.<action>". Store admins implicitly hold all of
them; staff hold only the codes listed on their Role. Roles themselves are
managed by store admins only and are not a delegable permission.
"""

RESOURCES: dict[str, str] = {
    "products": "Products",
    "orders": "Orders",
    "customers": "Customers",
    "users": "Team members",
}

ACTIONS: dict[str, str] = {
    "read": "View",
    "create": "Create",
    "update": "Edit",
    "delete": "Delete",
}

ALL_PERMISSIONS: list[str] = [f"{resource}.{action}" for resource in RESOURCES for action in ACTIONS]


def is_valid_permission(code: str) -> bool:
    return code in ALL_PERMISSIONS


def permission_catalog() -> dict:
    return {
        "resources": [{"key": key, "label": label} for key, label in RESOURCES.items()],
        "actions": [{"key": key, "label": label} for key, label in ACTIONS.items()],
        "permissions": ALL_PERMISSIONS,
    }
