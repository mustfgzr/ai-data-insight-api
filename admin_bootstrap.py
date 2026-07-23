from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from auth import hash_password
from database import SessionLocal
import models


ENV_FIELDS = ("ADMIN_BOOTSTRAP_FULL_NAME", "ADMIN_BOOTSTRAP_EMAIL", "ADMIN_BOOTSTRAP_PASSWORD")

load_dotenv()


def bootstrap_admin(db: Session) -> tuple[models.User, bool]:
    values = {field: os.getenv(field, "").strip() for field in ENV_FIELDS}
    if not all(values.values()):
        raise RuntimeError("Yonetici bootstrap degiskenleri tanimlanmadi")

    email = values["ADMIN_BOOTSTRAP_EMAIL"].lower()
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing is not None:
        if existing.role != "admin":
            raise RuntimeError("Bu e-posta zaten analist hesabina ait")
        return existing, False

    admin = models.User(
        full_name=" ".join(values["ADMIN_BOOTSTRAP_FULL_NAME"].split()),
        email=email,
        role="admin",
        must_change_password=False,
        hashed_password=hash_password(values["ADMIN_BOOTSTRAP_PASSWORD"]),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin, True


def main() -> None:
    db = SessionLocal()
    try:
        _admin, created = bootstrap_admin(db)
    finally:
        db.close()
    print("Yonetici hesabi olusturuldu." if created else "Yonetici hesabi zaten var.")


if __name__ == "__main__":
    main()
