# Riragia Social Hub — Version 1

A local Streamlit MVP with:
- User registration and login
- Feeds for community posts, with sponsored ad placements
- Reels for short videos, with sponsored ad placements
- Basic one-to-one text messaging
- User profiles (name, profile picture, faculty, bio, posts and reels)
- Marketplace product submissions
- Admin approval/rejection workflow for marketplace listings
- Basic admin controls for sponsored placements

## Run locally on Debian

Activate your virtual environment, then:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local address Streamlit prints (usually http://localhost:8501).

## First-run demo administrator

- Username: `admin`
- Password: `ChangeMe123!`

**Change this immediately before using the app with real users.** For this prototype, the admin account is created automatically on first launch. To reset the local demo database, stop Streamlit and delete `riragia.db`; it will be recreated on next launch.

## Local data

- `riragia.db` stores accounts, posts, reels, messages, marketplace listings and ad placements.
- `uploads/` stores uploaded photos and videos.
- Keep both when you want to preserve local data. Back them up together.

## Important prototype limitations

This is a first local prototype, not a production social network:
- Passwords use a basic hash for demonstration; replace with a modern password-hashing library (Argon2/bcrypt) before deployment.
- The demo admin credentials are not production-safe.
- No password reset, email/phone verification, reporting, blocking, moderation queue for posts/reels, likes, comments, notifications, search, or mobile-native reel experience yet.
- Messaging is basic text messaging; it is not end-to-end encrypted.
- Media uploads are stored on the machine running Streamlit. A deployed version needs managed object storage, upload limits, virus scanning and backups.
- Admin approval is a review workflow, not proof that an item is authentic or available. Establish seller verification and clear marketplace rules before accepting payments.
- The ad slots are demo placements, not a real advertising network or billing system.
- Streamlit's simple app flow is suitable for validating the idea, but a larger public platform will eventually need a backend API, proper authentication/authorization, database migrations, rate limiting, logging and deployment hardening.

## Suggested next development milestones

1. Add likes, comments, follows/friends and user search.
2. Add admin moderation/reporting for posts and reels.
3. Add product edit/delete, seller verification and listing expiry.
4. Add message inbox/unread indicators and attachments.
5. Add real ad campaign management, targeting rules and impression/click reporting.
6. Move to PostgreSQL and object storage for a hosted multi-user deployment.
