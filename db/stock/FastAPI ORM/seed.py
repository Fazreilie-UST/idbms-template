# app/seed.py
from app.models import User, Item
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

def seed_db(db: Session):
    # Mock users
    users = [
        User(email="rishin@decade.com", password="1234"),
        User(email="bob@example.com", password="hashed_password2"),
    ]
    
    # Mock items
    items = [
        Item(name="Item A", description="Description A"),
        Item(name="Item B", description="Description B"),
    ]

    try:
        for u in users:
            if not db.query(User).filter_by(email=u.email).first():
                db.add(u)
        for i in items:
            if not db.query(Item).filter_by(name=i.name).first():
                db.add(i)
        db.commit()
        print("✅ Mock data seeded successfully.")
    except IntegrityError:
        db.rollback()
        print("⚠️ Mock data already exists.")
    finally:
        db.close()