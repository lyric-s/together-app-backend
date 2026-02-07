from sqlmodel import Session, select
from app.database.init_ai_test_data import init_ai_test_data
from app.models.user import User
from app.models.mission import Mission

def test_init_ai_test_data(session: Session):
    """
    Test that AI test data seeding works correctly and is idempotent.
    """
    # 1. Run seeding
    init_ai_test_data(session)
    
    # 2. Verify suspicious users created
    spam_user = session.exec(select(User).where(User.email == "spam_user@example.com")).first()
    toxic_user = session.exec(select(User).where(User.email == "toxic_user@example.com")).first()
    
    assert spam_user is not None
    assert toxic_user is not None
    assert "spam" in spam_user.volunteer_profile.bio.lower()
    assert "toxic" in toxic_user.volunteer_profile.first_name.lower() or "foutez le camp" in toxic_user.volunteer_profile.bio.lower()

    # 3. Verify fraudulent mission created
    mission = session.exec(select(Mission).where(Mission.name == "ARGENT FACILE ET RAPIDE")).first()
    assert mission is not None
    assert "riche" in mission.description.lower()

    # 4. Test idempotency (run again should not fail or duplicate)
    init_ai_test_data(session)
    users = session.exec(select(User).where(User.email == "spam_user@example.com")).all()
    assert len(users) == 1