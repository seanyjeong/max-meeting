#!/usr/bin/env python3
"""Test JWT functionality only."""
import os
os.environ['SECRET_KEY'] = 'test-secret-key-32-bytes-minimum'
os.environ['JWT_SECRET'] = 'test-jwt-secret-32-bytes-minimum'
os.environ['AUTH_PASSWORD_HASH'] = 'dummy'
os.environ['DATABASE_URL'] = 'postgresql://localhost/test'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

from app.auth.jwt import create_access_token, create_refresh_token, verify_token

print("=== Testing JWT Tokens ===")
user_id = "1"

# Create tokens
access_token = create_access_token(subject=user_id)
refresh_token = create_refresh_token(subject=user_id)

print(f"✓ Access Token created (length: {len(access_token)})")
print(f"✓ Refresh Token created (length: {len(refresh_token)})")

# Verify tokens
access_payload = verify_token(access_token, token_type="access")
print(f"\n✓ Access Token verified:")
print(f"    Subject: {access_payload['sub']}")
print(f"    Type: {access_payload['type']}")
print(f"    Audience: {access_payload['aud']}")
print(f"    Issuer: {access_payload['iss']}")
print(f"    JTI: {access_payload['jti']}")

refresh_payload = verify_token(refresh_token, token_type="refresh")
print(f"\n✓ Refresh Token verified:")
print(f"    Subject: {refresh_payload['sub']}")
print(f"    Type: {refresh_payload['type']}")

print("\n=== Testing Token Type Validation ===")
try:
    verify_token(access_token, token_type="refresh")
    print("❌ ERROR: Should have rejected wrong token type!")
    exit(1)
except Exception as e:
    print(f"✓ Correctly rejected access token as refresh token")

try:
    verify_token(refresh_token, token_type="access")
    print("❌ ERROR: Should have rejected wrong token type!")
    exit(1)
except Exception as e:
    print(f"✓ Correctly rejected refresh token as access token")

print("\n=== Testing Invalid Token ===")
try:
    verify_token("invalid.token.here")
    print("❌ ERROR: Should have rejected invalid token!")
    exit(1)
except Exception as e:
    print(f"✓ Correctly rejected invalid token")

print("\n✅ All JWT tests passed!")
