import pytest, asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.users import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session", autouse=True)
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def init_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_admin_user() -> User:
    async with TestingSessionLocal() as session:
        user = User(email="admin@test.com", username="testadmin", full_name="Admin User",
                    hashed_password=get_password_hash("AdminPass123"), is_active=True, is_admin=True)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest.fixture
def admin_headers(test_admin_user: User) -> dict:
    token = create_access_token(subject=str(test_admin_user.id), claims={"email": test_admin_user.email, "is_admin": True})
    return {"Authorization": f"Bearer {token}"}
