from datetime import datetime, timezone, timedelta

from app.db.session import SessionLocal
from app.models.auth.refresh_token import RefreshToken


def main():
    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)
        revoked_cutoff = now - timedelta(days=30)

        deleted = (
            db.query(RefreshToken)
            .filter(
                (RefreshToken.expires_at < now)
                | (
                    (RefreshToken.revoked == True)
                    & (RefreshToken.revoked_at.isnot(None))
                    & (RefreshToken.revoked_at < revoked_cutoff)
                )
            )
            .delete(synchronize_session=False)
        )

        db.commit()

        print(f"Deleted {deleted} old refresh token records.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()