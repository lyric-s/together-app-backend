<!-- markdownlint-disable MD033 MD036 -->

# 🚀 Together API

<p align="center">
  <img src="https://img.shields.io/badge/Status-Online-success?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Version-0.2.0-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Docs-OpenAPI-green?style=for-the-badge" alt="Docs">
</p>

Welcome to the **Together API**, the backend connecting volunteers with non-profit organizations worldwide.

---

## 🔐 Authentication & Security

> **Important**: This API uses a unified authentication system. All users (Volunteers, Associations, Admins) authenticate via the same endpoint.

* **Endpoint**: `POST /auth/token`
* **Format**: OAuth2 Password Flow (form-data: `username`, `password`)
* **Response**: `access_token` (JWT), `refresh_token`, and `user_type`.

<details>
<summary><strong>🛡️ Security Features (Click to expand)</strong></summary>

* **Token Rotation**: Refresh tokens are one-time use. A new token is issued on every refresh.
* **Rate Limiting**: `5 req/min` on auth endpoints. Returns `429 Too Many Requests`.
* **Role-Based Access Control (RBAC)**: Strict permission checks based on `user_type`.

</details>

## 👥 User Roles

| Role | Description | Key Capabilities |
| :--- | :--- | :--- |
| **Volunteer** | Individual Helper | Search missions, apply, manage profile, favorites |
| **Association** | Non-Profit Org | Create missions, validate volunteers, upload docs |
| **Admin** | Platform Staff | Verify associations, moderate content, manage users |

## 📡 API Reference

<details>
<summary><strong>Common Status Codes</strong></summary>

| Code | Meaning |
| :--- | :--- |
| `200` | **OK** - Success |
| `201` | **Created** - Resource created |
| `400` | **Bad Request** - Validation error |
| `401` | **Unauthorized** - Invalid/Missing token |
| `403` | **Forbidden** - Insufficient permissions |
| `404` | **Not Found** - Resource missing |
| `409` | **Conflict** - Resource already exists |
| `422` | **Unprocessable** - Data schema error |
| `429` | **Too Many Requests** - Slow down! |

</details>

<details>
<summary><strong>Pagination Guide</strong></summary>

List endpoints generally accept:

* `offset`: Records to skip (default `0`)
* `limit`: Records to return (default `100`, max `100`)

Example: `GET /volunteers?offset=10&limit=5`

</details>

---

## 📖 API Usage Example

### Creating a Report

This example demonstrates the complete flow of creating a report against another user.

**Request:**

```http
POST /reports/ HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "type": "HARASSMENT",
  "target": "PROFILE",
  "reason": "This user has been sending inappropriate messages repeatedly.",
  "id_user_reported": 456
}
```

**Success Response (201 Created):**

```json
{
  "id_report": 789,
  "type": "HARASSMENT",
  "target": "PROFILE",
  "reason": "This user has been sending inappropriate messages repeatedly.",
  "id_user_reported": 456,
  "reporter_name": "John Doe",
  "reported_name": "Jane Smith",
  "state": "PENDING",
  "date_reporting": "2026-01-14T10:30:00Z"
}
```

**Error Response (409 Conflict):**

```json
{
  "detail": "Pending report already exists against user 456"
}
```

**Error Response (422 Validation Error):**

```json
{
  "detail": "You cannot report yourself"
}
```

---

*Built with ❤️ at IUT Paris - Rives de Seine*
