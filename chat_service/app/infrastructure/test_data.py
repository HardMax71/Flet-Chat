# app/infrastructure/test_data.py

from sqlalchemy import select

from app.infrastructure.models import User


async def init_test_data(session_factory, security_service) -> None:
    """Initialize test users for development/testing purposes."""
    async with session_factory() as session:
        # Check if test users already exist
        test_user1 = await session.scalar(select(User).where(User.username == "test"))
        test_user2 = await session.scalar(select(User).where(User.username == "alice"))

        if not test_user1:
            # Create test user 1
            hashed_password = security_service.get_password_hash("testpassword")
            test_user1 = User(
                username="test",
                email="test@example.com",
                hashed_password=hashed_password,
                is_active=True,
            )
            session.add(test_user1)

        if not test_user2:
            # Create test user 2
            hashed_password = security_service.get_password_hash("alicepassword")
            test_user2 = User(
                username="alice",
                email="alice@example.com",
                hashed_password=hashed_password,
                is_active=True,
            )
            session.add(test_user2)

        await session.commit()
