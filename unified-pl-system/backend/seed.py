import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, Base, engine  # noqa: E402
from models.user import User  # noqa: E402
from routers.auth_router import pwd_context  # noqa: E402


def seed():
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
    except Exception as e:
        print("\n[FAIL] DATABASE_UNAVAILABLE")
        print(f"Error: {e}")
        print("Suggested action: Start PostgreSQL service and run python run.py again.")
        sys.exit(1)
        
    try:
        # Remove any users that are not 'admin'
        other_users = db.query(User).filter(User.username != "admin").all()
        for u in other_users:
            db.delete(u)

        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            user = User(
                username="admin",
                email="admin@unifiedpl.com",
                hashed_password=pwd_context.hash("admin123"),
                role="Admin",
                is_active=True,
            )
            db.add(user)
            print("Created admin user.")
        else:
            user.hashed_password = pwd_context.hash("admin123")
            user.email = "admin@unifiedpl.com"
            user.role = "Admin"
            user.is_active = True
            print("Updated admin user credentials.")

        # Seed global system settings
        from models.recommendation import Setting
        settings_to_seed = {
            "enable_copilot": "true",
            "enable_forecast_engine": "true",
            "enable_recommendations": "true",
            "enable_notifications": "true",
        }
        for k, v in settings_to_seed.items():
            existing = db.query(Setting).filter(Setting.key == k).first()
            if not existing:
                db.add(Setting(key=k, value=v))
                print(f"Seeded setting: {k}={v}")
            else:
                existing.value = v
                print(f"Updated setting: {k}={v}")

        db.commit()
        
        # Seed demo dataset pre-flight to avoid HTTP 504 timeouts on first requests
        from services.pl_service import ensure_demo_data
        print("Pre-seeding demo datasets and anomaly detection data...")
        ensure_demo_data(db)

        print("Successfully seeded database with default admin credentials and system settings!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
