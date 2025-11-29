#!/usr/bin/env python3
"""Test script to debug 422 error on /packages endpoint."""
import requests
import json

API_URL = "http://localhost:8000"

# Authenticate first
auth_response = requests.post(f"{API_URL}/authenticate", json={"username": "ece30861defaultadminuser", "password": "correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"})
if auth_response.status_code != 200:
    print(f"Authentication failed: {auth_response.status_code} - {auth_response.text}")
    exit(1)

token = auth_response.json()["token"]
print(f"Authenticated successfully. Token: {token[:20]}...\n")

headers = {
    "Content-Type": "application/json",
    "X-Authorization": token
}

# Test 1: Empty body
print("Test 1: Empty body {}")
response = requests.post(f"{API_URL}/packages?offset=0&limit=50", headers=headers, json={})
print(f"Status: {response.status_code}")
print(f"Response: {response.text}\n")

# Test 2: None values
print("Test 2: All None values")
response = requests.post(f"{API_URL}/packages?offset=0&limit=50", headers=headers, json={"name": None, "version": None, "regex": None})
print(f"Status: {response.status_code}")
print(f"Response: {response.text}\n")

# Test 3: With a regex value
print("Test 3: With regex value")
response = requests.post(f"{API_URL}/packages?offset=0&limit=50", headers=headers, json={"regex": ".*"})
print(f"Status: {response.status_code}")
print(f"Response: {response.text}\n")
