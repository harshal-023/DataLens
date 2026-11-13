# Google Sheets Connector Setup Guide

## Overview

DataLens connects directly to Google Sheets via the official Google Sheets API v4 using OAuth 2.0. This allows users to import cloud spreadsheets, select individual worksheets (tabs), and automatically refresh data on a schedule.

---

## 1. Google Cloud Console Configuration

### Step 1: Create or Select a Google Cloud Project
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown in the top bar and click **New Project**.
3. Name your project (e.g. `DataLens Analytics Integration`) and click **Create**.

### Step 2: Enable Required APIs
1. In the navigation menu, go to **APIs & Services** > **Library**.
2. Search for and enable:
   - **Google Sheets API**
   - **Google Drive API** (used for spreadsheet metadata and discovery)

### Step 3: Configure OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**.
2. Select **External** (or **Internal** if using Google Workspace within your organization).
3. Fill in:
   - App name: `DataLens BI`
   - User support email: `support@yourdomain.com`
   - Developer contact email: `admin@yourdomain.com`
4. Under **Scopes**, click **Add or Remove Scopes** and select:
   - `https://www.googleapis.com/auth/spreadsheets.readonly`
   - `https://www.googleapis.com/auth/drive.readonly`
5. Click **Save and Continue**.

### Step 4: Create OAuth 2.0 Credentials
1. Go to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** > **OAuth client ID**.
3. Select **Web application** as Application type.
4. Add Authorized redirect URIs:
   - For local development: `http://localhost:5173/data-sources`
   - For production: `https://your-datalens-domain.com/data-sources`
5. Click **Create** and copy your:
   - **Client ID** (e.g. `123456789-abcdef.apps.googleusercontent.com`)
   - **Client Secret** (e.g. `GOCSPX-xyz...`)

---

## 2. Locating Your Spreadsheet ID

Open your Google Sheet in a web browser. The URL has the format:

```
https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0
                                      ▲
                                      │
                         Spreadsheet ID (44 characters)
```

Copy the string between `/d/` and `/edit`.

---

## 3. Configuring the Connection in DataLens

1. In DataLens, open **Data Sources** from the sidebar navigation.
2. Under **Available External Connectors**, click **Connect** on the **Google Sheets** card.
3. Enter a Connection Name (e.g. `Q4 Sales Pipeline Sheet`).
4. Paste the **Spreadsheet ID**.
5. Enter your **Client ID**, **Client Secret**, and **Refresh Token**.
6. Click **Test Connection** to verify OAuth authorization.
7. Click **Save Connection**.
8. Click **Browse** on the saved connection to inspect individual worksheet tabs (e.g. `Sheet1`, `Regions`, `Summary`) and click **Import** to start ingestion.

