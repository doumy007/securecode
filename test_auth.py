import asyncio
from app.models import Rol, Usuario, Proyecto, Auditoria
from app.database import async_session_factory
from app.auth.service import AuthService
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def test():
    async with async_session_factory() as db:
        service = AuthService(db)
        await service.create_roles_if_not_exist()
        print("Roles created OK")

        try:
            user = await service.register_user(
                username="admin", email="admin@sc.ai",
                password="Admin123!", nombre_completo="Admin",
                rol_id=1,
            )
            print(f"User created: {user.username}")
        except Exception as e:
            if "ya existe" in str(e):
                print("Admin user already exists")
            else:
                print(f"Register error: {e}")

        result = await db.execute(
            select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.username == "admin")
        )
        user = result.scalar_one_or_none()
        if user:
            rol_name = user.rol.nombre if user.rol else "unknown"
            token = service.create_access_token(user, rol_name=rol_name)
            print(f"JWT: {token[:60]}...")
            verified = await service.verify_access_token(token)
            print(f"Token verified: {verified.username if verified else 'FAIL'}")
            print("Auth module OK")


asyncio.run(test())
