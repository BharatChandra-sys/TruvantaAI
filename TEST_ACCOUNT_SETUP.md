# Test Account Setup

## Quick Test Account

Since the extension requires authentication, you can either:

### Option 1: Create Test Account (Recommended)

1. Click "Create Account" in the extension login page
2. Use these credentials:
   - Email: `test@test.com`
   - Password: `test123`
3. Account will be created in your local database

### Option 2: Use Existing Account

If you already have an account from production, you can login with those credentials. Your local backend will create a new user entry.

### Option 3: Manual Account Creation

Create an account via API:

```powershell
curl http://127.0.0.1:8000/auth/register `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"email":"test@test.com","password":"test123","name":"Test User"}' `
  -UseBasicParsing
```

This will return:
```json
{
  "token": "eyJ...",
  "user": {
    "id": 1,
    "email": "test@test.com",
    "name": "Test User"
  }
}
```

## Testing Without Account

The fact-checking API endpoints support optional authentication:
- `/check/stream` - Works without auth (limited rate)
- `/message` - Works without auth (limited rate)
- `/health` - Public endpoint

However, the extension UI requires login for:
- Chat history
- Saved claims
- User settings
- Rate limit upgrades

## Verify Login Works

After creating account:
1. Check extension shows your email in sidebar
2. Test a claim: "Coffee causes cancer"
3. Backend logs should show your user ID in requests

## Backend Logs to Watch

When logged in, you'll see:
```json
{"ts":"...", "level":"INFO", "msg":"User 1 checking claim"}
```

When not logged in:
```json
{"ts":"...", "level":"INFO", "msg":"Anonymous checking claim"}
```
