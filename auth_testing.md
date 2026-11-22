# Auth Testing Playbook

## JWT email/password
```
API=<REACT_APP_BACKEND_URL>/api
curl -c c.txt -X POST $API/auth/login -H "Content-Type: application/json" -d '{"email":"daniel.okafor@nexora.io","password":"Demo@12345"}'
curl -b c.txt $API/auth/me
```
Login returns {user, access_token} and sets `access_token` + `refresh_token` httpOnly cookies. Bearer is also accepted: `-H "Authorization: Bearer <access_token>"`.
Check in Mongo: users.password_hash starts with `$2b$`. There is a unique index on users.email and users.id.

## Google (Emergent-managed)
The frontend redirects to https://auth.emergentagent.com/?redirect=<origin>/overview. On return, `#session_id=...` is POSTed to /api/auth/google/session.
New users get `{status:"needs_mode", pending_token}` and the frontend shows /auth/choose-mode. Then POST /api/auth/google/complete issues the JWT cookies.
The full Google flow is human-verified only.

## RBAC checks
- Individual token -> GET /api/org/departments => 403
- Employee token -> GET /api/team/members => 403
- Non-demo user -> POST /api/demo/switch => 403
