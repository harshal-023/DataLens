# DataLens — PostgreSQL Database Setup Guide (Windows)

This document provides exact, step-by-step instructions for installing and configuring PostgreSQL 16 on Windows for the DataLens platform.

---

## 1. Prerequisites Check

Open PowerShell and check if PostgreSQL or Docker is already available:

```powershell
# Check for docker
Get-Command docker -ErrorAction SilentlyContinue

# Check for psql
Get-Command psql -ErrorAction SilentlyContinue

# Check if port 5432 is already listening
Test-NetConnection -ComputerName 127.0.0.1 -Port 5432
```

If port 5432 returns `False`, proceed with installation.

---

## 2. Option A: Native Windows Installation (Recommended)

1. **Download PostgreSQL 16:**
   - Download the official installer from EnterpriseDB: [PostgreSQL Windows Downloads](https://www.postgresql.org/download/windows/)
   - Select **PostgreSQL 16.x for Windows x86-64**.

2. **Run Installer:**
   - Run the downloaded `.exe` installer as Administrator.
   - Choose default installation directory: `C:\Program Files\PostgreSQL\16`.
   - Select all components: **PostgreSQL Server**, **pgAdmin 4**, **Stack Builder**, and **Command Line Tools**.
   - **Password:** Set the password for the superuser `postgres` (e.g., `postgres` for local development).
   - **Port:** Keep default port `5432`.
   - **Locale:** Choose `[Default locale]`.
   - Complete installation (uncheck Stack Builder at exit).

3. **Add `psql` to PATH (Optional but recommended):**
   ```powershell
   [Environment]::SetEnvironmentVariable(
       "Path",
       $env:Path + ";C:\Program Files\PostgreSQL\16\bin",
       [EnvironmentVariableTarget]::User
   )
   ```

4. **Verify Windows PostgreSQL Service:**
   ```powershell
   Get-Service -Name "postgresql-x64-16"
   # If stopped, start it:
   Start-Service -Name "postgresql-x64-16"
   ```

---

## 3. Option B: Docker Container

If Docker Desktop is installed:

```powershell
docker run -d `
  --name datalens-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=datalens `
  -p 5432:5432 `
  postgres:16-alpine
```

---

## 4. Option C: Windows Package Manager (winget)

```powershell
# Install PostgreSQL 16 via winget
winget install PostgreSQL.PostgreSQL.16 --accept-package-agreements --accept-source-agreements
```

---

## 5. Database Creation & User Provisioning

Once PostgreSQL is running on port 5432:

```powershell
# 1. Create the primary datalens database
& "C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres -h localhost -p 5432 datalens

# 2. (Optional) Create dedicated least-privilege application user
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost -p 5432 -c "CREATE USER datalens_app WITH PASSWORD 'secure_dev_password';"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost -p 5432 -c "GRANT ALL PRIVILEGES ON DATABASE datalens TO datalens_app;"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost -p 5432 -d datalens -c "GRANT ALL ON SCHEMA public TO datalens_app;"
```

---

## 6. Configure Backend `.env`

Copy `.env.example` to `backend/.env`:

```powershell
cd "d:\PE CP\backend"
Copy-Item .env.example .env
```

Ensure `DATABASE_URL` matches your local credentials:
```env
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/datalens"
```

---

## 7. Apply Alembic Migrations

```powershell
cd "d:\PE CP\backend"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

