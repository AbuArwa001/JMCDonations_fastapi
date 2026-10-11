"""
RBAC administration endpoints: roles, permissions and staff user management.

Mounted at /api/v1/rbac
"""
import uuid
import secrets
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict
from urllib.parse import urlparse, parse_qs

import firebase_admin
from firebase_admin import auth as fb_auth
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.users import User, Role
from app.core.permissions import (
    PERMISSIONS, WILDCARD, SUPER_ADMIN_ROLE, sanitize_permissions,
)
from app.core.security import get_password_hash
from app.schemas.rbac import (
    PermissionGroup, RoleCreate, RoleUpdate, RoleResponse, RoleSummary,
    StaffUserResponse, StaffUserCreate, StaffUserUpdate, MyAccessResponse, RbacStats,
)
from app.api.dependencies.auth import (
    get_current_active_user, get_current_admin_user, get_user_permissions,
    has_permission, require_permission,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Helpers ====================

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_wildcard_role(role: Optional[Role]) -> bool:
    return bool(role and WILDCARD in (role.permissions or []))


def _user_is_super(user: User, role: Optional[Role]) -> bool:
    if not user.is_admin or not user.is_active:
        return False
    return role is None or _is_wildcard_role(role)


async def _roles_by_id(db: AsyncSession) -> Dict[uuid.UUID, Role]:
    res = await db.execute(select(Role))
    return {r.id: r for r in res.scalars().all()}


def _serialize_user(user: User, roles: Dict[uuid.UUID, Role]) -> StaffUserResponse:
    role = roles.get(user.role_id) if user.role_id else None
    return StaffUserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        phone_number=user.phone_number,
        profile_image_url=user.profile_image_url,
        is_active=user.is_active,
        is_admin=user.is_admin,
        is_super_admin=_user_is_super(user, role),
        role=RoleSummary.model_validate(role) if role else None,
        ss_login=user.ss_login,
        firebase_uid=user.firebase_uid,
    )


async def _count_super_admins(db: AsyncSession) -> int:
    roles = await _roles_by_id(db)
    wildcard_ids = [rid for rid, r in roles.items() if _is_wildcard_role(r)]
    cond = User.role_id.is_(None)
    if wildcard_ids:
        cond = or_(cond, User.role_id.in_(wildcard_ids))
    res = await db.execute(
        select(func.count(User.id)).filter(User.is_admin.is_(True), User.is_active.is_(True), cond)
    )
    return int(res.scalar() or 0)


async def _actor_perms(db: AsyncSession, actor: User) -> set[str]:
    return await get_user_permissions(db, actor)


def _firebase_ready() -> bool:
    return bool(firebase_admin._apps)


def _fb_set_admin_claim(uid: str, is_admin: bool) -> None:
    record = fb_auth.get_user(uid)
    claims = dict(record.custom_claims or {})
    claims["admin"] = is_admin
    fb_auth.set_custom_user_claims(uid, claims)


def _fb_ensure_user(email: str, password: Optional[str], display_name: str):
    """Return (firebase_user_record, created: bool)."""
    try:
        return fb_auth.get_user_by_email(email), False
    except fb_auth.UserNotFoundError:
        rec = fb_auth.create_user(
            email=email,
            password=password or secrets.token_urlsafe(16),
            display_name=display_name,
            email_verified=False,
        )
        return rec, True


async def _sync_admin_claim(user: User) -> None:
    """Keep the Firebase `admin` custom claim aligned with local portal access.
    Important: Firebase sync re-grants is_admin on login if the claim is set."""
    if not user.firebase_uid or not _firebase_ready():
        return
    try:
        await run_in_threadpool(_fb_set_admin_claim, user.firebase_uid, bool(user.is_admin and user.is_active))
    except Exception as e:  # pragma: no cover - external service
        logger.warning(f"Failed to sync Firebase admin claim for {user.email}: {e}")


async def _unique_username(db: AsyncSession, email: str) -> str:
    base = email.split("@")[0].lower() or f"staff_{secrets.token_hex(3)}"
    candidate, n = base, 1
    while (await db.execute(select(User.id).filter(User.username == candidate))).first():
        candidate = f"{base}_{n}"
        n += 1
    return candidate


async def _get_role_or_404(db: AsyncSession, role_id: uuid.UUID) -> Role:
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


def _guard_role_assignment(actor_perms: set[str], role: Optional[Role]) -> None:
    """Prevent privilege escalation: you can't grant what you don't hold."""
    if role is None:
        return
    role_perms = set(role.permissions or [])
    if WILDCARD in actor_perms:
        return
    if WILDCARD in role_perms or not role_perms.issubset(actor_perms):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot assign a role with more privileges than your own",
        )


def _format_custom_reset_link(
    raw_link: Optional[str],
    email: str,
    request: Optional[Request] = None,
) -> Optional[str]:
    """
    Transforms Firebase default action URL:
      https://<project>.firebaseapp.com/__/auth/action?mode=resetPassword&oobCode=...
    Into our luxury, white-labeled dashboard reset URL:
      https://admin.jamiamosque.co.ke/reset-password?oobCode=...&email=...
    """
    if not raw_link:
        return raw_link
    try:
        parsed = urlparse(raw_link)
        qs = parse_qs(parsed.query)
        oob_code = qs.get("oobCode", [""])[0]
        if not oob_code:
            return raw_link

        base_url = None
        if request:
            origin = request.headers.get("origin")
            if not origin:
                referer = request.headers.get("referer")
                if referer:
                    ref_p = urlparse(referer)
                    origin = f"{ref_p.scheme}://{ref_p.netloc}"
            if origin:
                base_url = origin.rstrip("/")

        if not base_url:
            base_url = getattr(settings, "ADMIN_DASHBOARD_URL", "http://localhost:3000").rstrip("/")

        return f"{base_url}/reset-password?oobCode={oob_code}&email={email}"
    except Exception as e:
        logger.warning(f"Error formatting custom reset link: {e}")
        return raw_link


# ==================== Current user access ====================

@router.get("/me", response_model=MyAccessResponse)
async def my_access(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the caller's role and effective permissions (used by the dashboard)."""
    roles = await _roles_by_id(db)
    perms = await get_user_permissions(db, current_user)
    return MyAccessResponse(
        user=_serialize_user(current_user, roles),
        permissions=sorted(perms),
        is_super_admin=WILDCARD in perms,
    )


@router.get("/permissions", response_model=List[PermissionGroup])
async def list_permissions(current_user: User = Depends(get_current_admin_user)):
    """Full permission catalog grouped by module."""
    groups: Dict[str, list] = {}
    for p in PERMISSIONS:
        groups.setdefault(p["group"], []).append(p)
    return [{"group": g, "permissions": items} for g, items in groups.items()]


@router.get("/stats", response_model=RbacStats)
async def rbac_stats(
    current_user: User = Depends(require_permission("users.manage", "roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count(User.id)).filter(User.is_admin.is_(True)))).scalar() or 0
    active = (await db.execute(
        select(func.count(User.id)).filter(User.is_admin.is_(True), User.is_active.is_(True))
    )).scalar() or 0
    unassigned = (await db.execute(
        select(func.count(User.id)).filter(User.is_admin.is_(True), User.role_id.is_(None))
    )).scalar() or 0
    roles = (await db.execute(select(func.count(Role.id)))).scalar() or 0
    return RbacStats(
        total_staff=total, active_staff=active, roles=roles,
        unassigned=unassigned, super_admins=await _count_super_admins(db),
    )


# ==================== Roles ====================

async def _role_response(db: AsyncSession, role: Role) -> RoleResponse:
    count = (await db.execute(
        select(func.count(User.id)).filter(User.role_id == role.id, User.is_admin.is_(True))
    )).scalar() or 0
    return RoleResponse(
        id=role.id, role_name=role.role_name, description=role.description,
        permissions=list(role.permissions or []), color=role.color,
        is_system=bool(role.is_system), user_count=count,
        created_at=role.created_at, updated_at=role.updated_at,
    )


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(require_permission("users.manage", "roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Role).order_by(Role.is_system.desc(), Role.role_name))
    return [await _role_response(db, r) for r in res.scalars().all()]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    current_user: User = Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    name = role_in.role_name.strip()
    if (await db.execute(select(Role.id).filter(func.lower(Role.role_name) == name.lower()))).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A role with this name already exists")

    perms = [p for p in sanitize_permissions(role_in.permissions) if p != WILDCARD]
    actor_perms = await _actor_perms(db, current_user)
    if WILDCARD not in actor_perms and not set(perms).issubset(actor_perms):
        raise HTTPException(status_code=403, detail="You cannot grant permissions you do not hold")

    role = Role(
        role_name=name, description=role_in.description, permissions=perms,
        color=role_in.color, is_system=False, created_at=_now(), updated_at=_now(),
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return await _role_response(db, role)


@router.put("/roles/{role_id}", response_model=RoleResponse)
@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID,
    role_in: RoleUpdate,
    current_user: User = Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    role = await _get_role_or_404(db, role_id)
    actor_perms = await _actor_perms(db, current_user)

    if role.is_system and (role_in.permissions is not None or role_in.role_name not in (None, role.role_name)):
        raise HTTPException(status_code=400, detail="System roles cannot be renamed or have their permissions changed")

    if role_in.role_name and role_in.role_name.strip() != role.role_name:
        name = role_in.role_name.strip()
        clash = await db.execute(
            select(Role.id).filter(func.lower(Role.role_name) == name.lower(), Role.id != role.id)
        )
        if clash.first():
            raise HTTPException(status_code=409, detail="A role with this name already exists")
        role.role_name = name

    if role_in.permissions is not None:
        perms = [p for p in sanitize_permissions(role_in.permissions) if p != WILDCARD]
        if WILDCARD not in actor_perms and not set(perms).issubset(actor_perms):
            raise HTTPException(status_code=403, detail="You cannot grant permissions you do not hold")
        role.permissions = perms
    if role_in.description is not None:
        role.description = role_in.description
    if role_in.color is not None:
        role.color = role_in.color

    role.updated_at = _now()
    await db.commit()
    await db.refresh(role)
    return await _role_response(db, role)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: uuid.UUID,
    current_user: User = Depends(require_permission("roles.manage")),
    db: AsyncSession = Depends(get_db),
):
    role = await _get_role_or_404(db, role_id)
    if role.is_system:
        raise HTTPException(status_code=400, detail="System roles cannot be deleted")
    in_use = (await db.execute(
        select(func.count(User.id)).filter(User.role_id == role.id, User.is_admin.is_(True))
    )).scalar() or 0
    if in_use:
        raise HTTPException(
            status_code=400,
            detail=f"Role is assigned to {in_use} staff member(s). Reassign them before deleting.",
        )
    await db.delete(role)
    await db.commit()


# ==================== Staff users ====================

@router.get("/users", response_model=List[StaffUserResponse])
async def list_staff_users(
    scope: str = Query("staff", pattern="^(staff|all)$"),
    search: Optional[str] = None,
    role_id: Optional[uuid.UUID] = None,
    limit: int = Query(200, le=500),
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    """List staff (portal users). Use scope=all + search to find app users to promote."""
    q = select(User)
    if scope == "staff":
        q = q.filter(User.is_admin.is_(True))
    if role_id:
        q = q.filter(User.role_id == role_id)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(or_(User.full_name.ilike(like), User.email.ilike(like), User.username.ilike(like)))
    q = q.order_by(User.is_admin.desc(), User.full_name).limit(limit)
    users = (await db.execute(q)).scalars().all()
    roles = await _roles_by_id(db)
    return [_serialize_user(u, roles) for u in users]


class StaffInviteResponse(BaseModel):
    user: StaffUserResponse
    created: bool
    firebase_synced: bool
    password_reset_link: Optional[str] = None


@router.post("/users", response_model=StaffInviteResponse, status_code=status.HTTP_201_CREATED)
async def create_staff_user(
    user_in: StaffUserCreate,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    """
    Grant portal access to a person. If they already exist (e.g. a mobile app user),
    they are promoted; otherwise a new account is created (in Firebase when configured).
    """
    actor_perms = await _actor_perms(db, current_user)
    role = await _get_role_or_404(db, user_in.role_id) if user_in.role_id else None
    if role is None:
        raise HTTPException(status_code=400, detail="Please select a role for this staff member")
    _guard_role_assignment(actor_perms, role)

    email = user_in.email.lower().strip()
    user = (await db.execute(select(User).filter(func.lower(User.email) == email))).scalars().first()
    created = user is None

    firebase_synced, reset_link, fb_uid = False, None, None
    if _firebase_ready():
        try:
            rec, fb_created = await run_in_threadpool(_fb_ensure_user, email, user_in.password, user_in.full_name)
            fb_uid = rec.uid
            firebase_synced = True
            if fb_created and not user_in.password:
                reset_link = await run_in_threadpool(fb_auth.generate_password_reset_link, email)
        except Exception as e:
            logger.error(f"Firebase user provisioning failed for {email}: {e}")
            raise HTTPException(status_code=502, detail=f"Could not provision Firebase account: {e}")

    if created:
        user = User(
            email=email,
            username=await _unique_username(db, email),
            full_name=user_in.full_name.strip(),
            phone_number=user_in.phone_number,
            hashed_password=get_password_hash(user_in.password) if user_in.password else None,
            firebase_uid=fb_uid,
            is_active=True,
            is_admin=True,
            role_id=role.id,
        )
        db.add(user)
    else:
        if user.is_admin and user.id == current_user.id:
            raise HTTPException(status_code=400, detail="You already have portal access")
        user.is_admin = True
        user.is_active = True
        user.role_id = role.id
        if user_in.full_name:
            user.full_name = user_in.full_name.strip()
        if user_in.phone_number:
            user.phone_number = user_in.phone_number
        if fb_uid and not user.firebase_uid:
            user.firebase_uid = fb_uid

    await db.commit()
    await db.refresh(user)
    await _sync_admin_claim(user)

    roles = await _roles_by_id(db)
    return StaffInviteResponse(
        user=_serialize_user(user, roles), created=created,
        firebase_synced=firebase_synced, password_reset_link=reset_link,
    )


@router.patch("/users/{user_id}", response_model=StaffUserResponse)
async def update_staff_user(
    user_id: uuid.UUID,
    user_in: StaffUserUpdate,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    actor_perms = await _actor_perms(db, current_user)
    roles = await _roles_by_id(db)
    current_role = roles.get(user.role_id) if user.role_id else None
    target_was_super = _user_is_super(user, current_role)

    if target_was_super and WILDCARD not in actor_perms:
        raise HTTPException(status_code=403, detail="Only a Super Admin can modify another Super Admin")

    is_self = user.id == current_user.id
    access_change = user_in.role_id is not None or user_in.clear_role \
        or user_in.is_active is not None or user_in.is_admin is not None
    if is_self and access_change:
        raise HTTPException(status_code=400, detail="You cannot change your own role or access level")

    if user_in.role_id is not None:
        new_role = await _get_role_or_404(db, user_in.role_id)
        _guard_role_assignment(actor_perms, new_role)
        user.role_id = new_role.id
    elif user_in.clear_role:
        if WILDCARD not in actor_perms:
            raise HTTPException(status_code=403, detail="Only a Super Admin can clear a role")
        user.role_id = None
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.is_admin is not None:
        user.is_admin = user_in.is_admin
    if user_in.full_name is not None:
        user.full_name = user_in.full_name.strip()
    if user_in.phone_number is not None:
        user.phone_number = user_in.phone_number

    # Never allow the portal to end up without an active Super Admin.
    new_role = roles.get(user.role_id) if user.role_id else None
    if user.role_id and user.role_id not in roles:
        new_role = await db.get(Role, user.role_id)
    if target_was_super and not _user_is_super(user, new_role):
        if await _count_super_admins(db) <= 1:
            await db.rollback()
            raise HTTPException(status_code=400, detail="At least one active Super Admin must remain")

    await db.commit()
    await db.refresh(user)
    await _sync_admin_claim(user)
    return _serialize_user(user, await _roles_by_id(db))


@router.post("/users/{user_id}/password-reset")
async def staff_password_reset_link(
    user_id: uuid.UUID,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a Firebase password reset link that can be shared with the staff member."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _firebase_ready():
        raise HTTPException(status_code=503, detail="Firebase is not configured on the server")
    try:
        link = await run_in_threadpool(fb_auth.generate_password_reset_link, user.email)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not generate reset link: {e}")
    return {"email": user.email, "password_reset_link": link}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_staff_access(
    user_id: uuid.UUID,
    current_user: User = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke portal access (the underlying account is kept, e.g. for mobile app use)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot revoke your own access")

    actor_perms = await _actor_perms(db, current_user)
    role = await db.get(Role, user.role_id) if user.role_id else None
    if _user_is_super(user, role):
        if WILDCARD not in actor_perms:
            raise HTTPException(status_code=403, detail="Only a Super Admin can revoke another Super Admin")
        if await _count_super_admins(db) <= 1:
            raise HTTPException(status_code=400, detail="At least one active Super Admin must remain")

    user.is_admin = False
    user.role_id = None
    await db.commit()
    await db.refresh(user)
    await _sync_admin_claim(user)


# ==================== Seeding ====================

async def ensure_default_roles(db: AsyncSession) -> None:
    """Idempotently create the built-in roles (called on application startup)."""
    from app.core.permissions import DEFAULT_ROLES

    existing = {r.role_name.lower(): r for r in (await db.execute(select(Role))).scalars().all()}
    changed = False
    for spec in DEFAULT_ROLES:
        role = existing.get(spec["role_name"].lower())
        if role is None:
            db.add(Role(**spec, created_at=_now(), updated_at=_now()))
            changed = True
        elif spec["role_name"] == SUPER_ADMIN_ROLE and (
            not role.is_system or WILDCARD not in (role.permissions or [])
        ):
            role.is_system = True
            role.permissions = [WILDCARD]
            changed = True
        elif role.permissions is None:
            role.permissions = spec["permissions"]
            changed = True
    if changed:
        await db.commit()
