#!/usr/bin/env python3
"""Manual test script for JWT authentication."""
import os
os.environ['SECRET_KEY'] = 'test-secret-key-32-bytes-minimum'
os.environ['JWT_SECRET'] = 'test-jwt-secret-32-bytes-minimum'
os.environ['AUTH_PASSWORD_HASH'] = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIeWeCrm4.'  # 'password'
os.environ['DATABASE_URL'] = 'postgresql://localhost/test'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

from app.auth.password import verify_password, get_password_hash
from app.auth.jwt import create_access_token, create_refresh_token, verify_token

print("=== Testing Password Hashing ===")
password = "testpassword123"
hashed = get_password_hash(password)
print(f"Password: {password}")
print(f"Hashed: {hashed[:50]}...")
print(f"Verify correct: {verify_password(password, hashed)}")
print(f"Verify wrong: {verify_password('wrong', hashed)}")

print("\n=== Testing JWT Tokens ===")
user_id = "1"

# Create tokens
access_token = create_access_token(subject=user_id)
refresh_token = create_refresh_token(subject=user_id)

print(f"Access Token (first 50 chars): {access_token[:50]}...")
print(f"Refresh Token (first 50 chars): {refresh_token[:50]}...")

# Verify tokens
access_payload = verify_token(access_token, token_type="access")
print(f"\nAccess Token Payload:")
print(f"  Subject: {access_payload['sub']}")
print(f"  Type: {access_payload['type']}")
print(f"  Audience: {access_payload['aud']}")
print(f"  Issuer: {access_payload['iss']}")

refresh_payload = verify_token(refresh_token, token_type="refresh")
print(f"\nRefresh Token Payload:")
print(f"  Subject: {refresh_payload['sub']}")
print(f"  Type: {refresh_payload['type']}")

print("\n=== Testing Token Type Validation ===")
try:
    verify_token(access_token, token_type="refresh")
    print("ERROR: Should have failed!")
except Exception as e:
    print(f"Correctly rejected access token as refresh: {type(e).__name__}")

print("\n✅ All manual tests passed!")
