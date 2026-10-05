# Tests

pytest suite covering core paths. Talks to backend via docker network; no frontend required.

## Run

Outside container (with Python + Docker):
  cd backend
  pip install -r requirements.txt
  IELTS_API_DIRECT=http://host.docker.internal:8000/api pytest -v

Inside container:
  docker exec -it ielts-writeup-backend-1 pytest /app/tests -v

## Configuration

- IELTS_API_DIRECT: backend base URL (default http://host.docker.internal:8000/api)
- IELTS_ADMIN_USER / IELTS_ADMIN_PASS: admin creds for tests

## Modules

- test_auth.py: login, rate limit, invite uniqueness, weak password rejection
- test_admin.py: models/users/invites/redeems listing, unauthorized blocked
- test_grading.py: submit, status, cancel+refund, rename title, length limits
- test_security.py: SSRF block, extract_json strict, JWT_SECRET strength

## Notes

Some tests require admin to have credits (e.g. cancel refund test). Running multiple
times drains credits. Use docker compose up -d --force-recreate backend to re-seed
admin credits (9999).
