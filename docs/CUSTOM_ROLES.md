# DataLens – Custom Roles Management Engine

## 1. Overview
Custom Roles allow workspace administrators to define tailored functional roles (e.g., "Data Steward", "Compliance Auditor", "Executive Viewer") with specific combinations of granular permissions.

---

## 2. System Role Protection & Lockout Prevention
- **System Roles (`owner`, `admin`, `editor`, `viewer`)**: Immutably defined and protected. Direct edits or deletions of system roles are rejected with `HTTP 403 Forbidden`.
- **Owner Lockout Invariant**: The workspace Owner can never be assigned a restricted custom role or demoted. Ownership transfer is a distinct, audited workflow.
- **Privilege Escalation Prevention**: An administrator cannot grant permissions in a custom role that they do not possess themselves.

---

## 3. Custom Role Operations
- **Creation**: Defines role name, description, and list of permission codes.
- **Modification**: Updates name, description, and permission sets.
- **Duplication**: Clones an existing role with all its permission mappings as a starting template.
- **Safe Deletion**: Deleting a custom role automatically unassigns active members and safely defaults them to `viewer` without corrupting workspace memberships.

---

## 4. API Endpoints
- `GET /api/v1/roles`: List workspace custom roles.
- `POST /api/v1/roles`: Create custom role.
- `PATCH /api/v1/roles/{role_id}`: Update custom role.
- `POST /api/v1/roles/{role_id}/duplicate`: Duplicate custom role.
- `DELETE /api/v1/roles/{role_id}`: Safely delete custom role.
- `POST /api/v1/roles/assign`: Assign custom role to a workspace member.

