# DataLens – Automated Business Report Sharing Engine

## 1. Overview
The Report Sharing Engine provides controlled distribution of generated business reports (PDF, DOCX, XLSX, and CSV) to team members and external stakeholders with provenance tracking and expiring download tokens.

---

## 2. Capabilities
1. **Member-Level Report Sharing**:
   - Grant workspace members access with Viewer or Editor permissions.
   - Automatically notifies recipients via in-app notification center and optional email alert.
2. **Controlled Download Links**:
   - Generates expiring download links for reports.
   - Optional password protection using SHA-256 password verification.
   - Increments download counter (`access_count`) on each retrieval.
   - Immediate administrative revocation.

---

## 3. Streaming Download Endpoint
When a client resolves a public report link:
- Resolves token hash against `share_access_tokens`.
- Validates expiration and password match.
- Streams the report file bytes with appropriate MIME types:
  - PDF: `application/pdf`
  - DOCX: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - XLSX: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  - CSV: `text/csv`
- Sets `Content-Disposition: attachment; filename="<report_name>.<ext>"`.

---

## 4. API Endpoints
- `POST /api/v1/reports/{report_id}/shares`: Share report with member.
- `GET /api/v1/reports/{report_id}/shares`: List report member shares.
- `DELETE /api/v1/reports/{report_id}/shares/{share_id}`: Revoke report member share.
- `POST /api/v1/reports/{report_id}/links`: Create expiring report download link.
- `GET /api/v1/reports/{report_id}/links`: List report share links.
- `DELETE /api/v1/reports/{report_id}/links/{token_id}`: Revoke report share link.
- `POST /api/v1/shared/reports/{token}/download`: Download shared report file bytes.

