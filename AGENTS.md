# SupportMaster Development Guidelines & Rules

This document outlines safety, security, and rendering guidelines that must be strictly followed when writing or modifying code in this codebase.

---

## 1. Security & Tenant Boundaries
* **Rule**: Every HTTP endpoint or service method that accesses or updates a case run or review task MUST verify that the resource owner matches the authenticated operator's tenant boundary.
* **Implementation Pattern**:
  ```python
  run_state = store.load_state(task.run_id)
  if run_state.tenant_id != auth.principal.tenant_id:
      raise TenantAccessError("Access denied: tenant boundary violation.")
  ```

---

## 2. Dynamic Page Escaping
* **Rule**: To prevent cross-site scripting (XSS) and injection vulnerabilities, all dynamic content rendered in HTML templates (such as user-supplied descriptions or agent outputs) MUST be passed through the `escape()` function.
* **Implementation Pattern**:
  ```python
  from html import escape
  # Always wrap outputs
  return f"<pre>{escape(result)}</pre>"
  ```

---

## 3. Resumption Idempotency Keys
* **Rule**: Whenever resuming a workflow task in a SQLite database worker queue, you must enqueue the task with a unique idempotency key containing a random suffix to prevent task claim collisions.
* **Implementation Pattern**:
  ```python
  from uuid import uuid4
  new_idempotency_key = f"{run_id}:adk_workflow:resume-{uuid4().hex[:8]}"
  ```
