# EscapeArrow

Modular arrow puzzle game, Android Capacitor project, FastAPI backend and separate browser admin dashboard. Neon palette: #121214 / #2A2A2E / #00F5D4 / #FFEE55 / #FF5A5F.

## Run locally on Windows

Install Python 3.12 and Node.js 22+. Extract this ZIP, open its folder in VS Code, then run in PowerShell:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000. Players enter the game directly without creating an account or entering an OTP. A guest profile is created automatically so gameplay, profile details, history, coins, and progress work immediately. Production refuses console OTP mode.

For macOS/Linux use `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt`, `cp .env.example .env` and `.venv/bin/python -m uvicorn app.main:app --reload`.

## Open your administrator dashboard

Edit `backend/app/config.py` and set `OWNER_EMAIL`, `OWNER_PHONE`, and `OWNER_PASSWORD` to the one owner credential. Then visit http://localhost:8000/admin/ and use that credential. Player accounts cannot use the admin login, and the old `make-admin` database flag is not accepted by admin APIs.

## Deploy everything on Render

The repository includes `render.yaml`. In Render choose **New > Blueprint**, connect this repository, and select the folder containing `render.yaml`. Render creates the Docker web service and PostgreSQL database together. Set the prompted owner and SMTP secrets, then deploy. The player site is `/`, and the owner dashboard is `/admin/` on the same Render URL.

## Android

The `android/` native project is included. An APK is NOT included; it requires the Android SDK and your backend URL. From the project root:

```powershell
npm ci
$env:API_URL="https://YOUR-BACKEND-DOMAIN"
npm run android:sync
npm run android:open
```

Install Android Studio 2025.2.1+ and SDK 36. Use its bundled JDK. In Android Studio build a debug APK for testing or use Generate Signed App Bundle / APK for release. Store the signing key privately. See the implementation manual for exact steps. Never place provider secrets in client/config.js or Android assets.

## Main folders

- `client/src`: API, authentication, game UI, profile, audio and navigation modules.
- `admin`: administrator UI, metrics, charts, player search and reviews.
- `backend/app/game.py`: pure board generation, collision, rating and payout rules.
- `backend/app/routes`: accounts, gameplay, profiles and administrator endpoints.
- `backend/app/models.py`: database tables; `db.py`: transactions; `providers.py`: email/SMS delivery.
- `backend/tests`: rule and API integration tests.
- `android`: generated native Android project.
- `docs`: PDF/DOCX manuals, OpenAPI JSON, SQL schema and architecture diagrams.

## Validation

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

See `docs/VALIDATION.md` for actual test outcomes and untested external services. The included guides describe implementation decisions and production setup. This is a source release, not a live hosted service or signed APK.
