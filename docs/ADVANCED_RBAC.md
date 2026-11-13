# DataLens – Advanced Role-Based Access Control (RBAC) & RLAC Architecture

## 1. Overview
Phase 5C delivers an enterprise-grade authorization engine combining coarse-grained workspace role hierarchies with fine-grained granular permissions and resource-level access control (RLAC).

---

## 2. Granular Permissions Catalog
Permissions are structured as `resource:action` tokens:
- **Datasets**: `dataset:view`, `dataset:create`, `dataset:edit`, `dataset:delete`, `dataset:export`
- **Data Sources**: `datasource:manage`
- **Transformations**: `transformation:create`, `transformation:execute`
- **Dashboards**: `dashboard:view`, `dashboard:create`, `dashboard:share`
- **Reports**: `report:generate`, `report:download`, `report:share`
- **Discussions**: `comment:manage`
- **Administration**: `member:manage`, `workspace:configure`
- **Governance & Audit**: `audit:view`, `security_policy:manage`, `governance:manage`, `governance:bypass`

---

## 3. Resource-Level Access Control (RLAC) Precedence Rules
Resource permissions are evaluated via `GovernanceService.check_resource_access()` using a strict 4-step hierarchy:
1. **Workspace Owner**: Has universal access. Cannot be locked out.
2. **Explicit Deny (`is_denied = True`)**: Overrides all other grants. Immediately rejects requests.
3. **Explicit Resource Grant (`is_denied = False`)**: Grants specified `viewer`, `editor`, or `admin` access on that specific asset.
4. **Workspace Role Fallback**: If no resource-level policy matches, the member's system or custom role capabilities apply.

---

## 4. Backend Enforcement
All endpoints enforce authorization at the controller layer via `GovernanceService.has_workspace_permission()` and `GovernanceService.check_resource_access()`. The frontend UI adapts visibility based on backend permissions, but backend security never relies on client-side state.

