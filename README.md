# HousePlanner

HousePlanner is an AI-assisted home design and cost-planning application. It has a React web client for signing in and viewing role-based workspaces, plus an ASP.NET Core API that verifies Firebase authentication tokens.

## Tech stack

- **Frontend:** React, TypeScript, Vite, Redux Toolkit, Tailwind CSS, Firebase Authentication
- **Backend:** ASP.NET Core 10, Firebase Admin SDK, Swagger/OpenAPI

## Project structure

```text
HousePlanner-Web/     React frontend
HousePlanner.API/     ASP.NET Core API
```

## Prerequisites

Install the following before you begin:

- [Node.js](https://nodejs.org/) 20 or later (npm is included)
- [.NET SDK 10](https://dotnet.microsoft.com/download)
- A Firebase project with Email/Password authentication enabled

## Quick start

Run the API and frontend in separate terminal windows.

### 1. Configure Firebase

1. Create or open a project in the [Firebase Console](https://console.firebase.google.com/).
2. In **Authentication** → **Sign-in method**, enable **Email/Password**.
3. Create a Firebase web app and copy its configuration values.
4. In **Project settings** → **Service accounts**, generate a new private key.

Place the downloaded private key at:

```text
HousePlanner.API/firebase-service-account.json
```

This filename is ignored by Git. Never commit a Firebase service-account file or a real `.env` file.

### 2. Configure and start the API

```bash
cd HousePlanner.API
dotnet restore
dotnet dev-certs https --trust
dotnet run
```

The API runs at `https://localhost:7193` in the default HTTPS profile. When running in Development, Swagger is available at [https://localhost:7193/swagger](https://localhost:7193/swagger).

Alternatively, set `GOOGLE_APPLICATION_CREDENTIALS` to the absolute path of your Firebase service-account JSON file instead of placing it in the API directory.

### 3. Configure and start the frontend

In a new terminal, from the repository root:

```bash
cd HousePlanner-Web
cp .env.example .env
npm install
npm run dev
```

Update `HousePlanner-Web/.env` with your Firebase web-app values. Use the local API address below:

```ini
VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
VITE_API_BASE_URL=https://localhost:7193/api/v1
```

Open the address shown by Vite, normally [http://localhost:5173](http://localhost:5173).

## Authentication flow

1. The user signs in through Firebase in the web client.
2. The client sends the Firebase ID token to `POST /api/v1/auth/verify`.
3. The API verifies the token with the Firebase Admin SDK and returns the user profile and role.

At present, the API assigns the **Architect** role to emails containing `architect`; every other authenticated user receives the **Contractor** role. This is temporary role-mapping logic until persistent user roles are added.

## Useful commands

| Component | Command | Purpose |
| --- | --- | --- |
| Frontend | `npm run dev` | Start the Vite development server |
| Frontend | `npm run build` | Type-check and create a production build |
| Frontend | `npm run lint` | Run linting |
| API | `dotnet run` | Start the API |
| API | `dotnet build` | Build the API |

## Before pushing to GitHub

The root `.gitignore` excludes dependencies, build outputs, local environment files, and Firebase credentials. Check what will be committed before your first push:

```bash
git add .
git status
git commit -m "feat: initial HousePlanner application setup"
```

Do not add `HousePlanner-Web/.env` or `HousePlanner.API/firebase-service-account.json` manually. Commit `HousePlanner-Web/.env.example` so other contributors know which values they need.
