import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
import backend.routers.registration_wizard as wizard

client = TestClient(app)

def test_atomic_registration():
    print("Testing Atomic Single-Request Registration...")
    payload = {
        "team_name": f"AtomicSquad_{uuid_hex()}",
        "college_name": "Anna University",
        "track": "Quantum Cryptography",
        "leader_name": "Test Lead",
        "leader_phone": "9876543210",
        "leader_email": f"lead_{uuid_hex()}@example.com",
        "leader_degree": "B.Tech",
        "leader_department": "ECE",
        "leader_year": "3rd Year",
        "leader_gender": "Male",
        "members": json.dumps([
            {"name": "M2", "email": f"m2_{uuid_hex()}@example.com", "phone": "9876543211", "gender": "Female", "degree": "B.Tech", "department": "ECE", "year": "3rd Year"},
            {"name": "M3", "email": f"m3_{uuid_hex()}@example.com", "phone": "9876543212", "gender": "Male", "degree": "B.Tech", "department": "ECE", "year": "3rd Year"},
            {"name": "M4", "email": f"m4_{uuid_hex()}@example.com", "phone": "9876543213", "gender": "Female", "degree": "B.Tech", "department": "ECE", "year": "3rd Year"}
        ]),
        "utr_number": "123456789012"
    }

    res = client.post("/api/register", data=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["success"] is True
    assert "redirect_url" in data
    assert data["username"] == payload["leader_email"]
    assert "password" in data
    print(f"[OK] Atomic registration passed! Team: {data['team_code']}, Redirect: {data['redirect_url']}")

def test_isolated_lambda_verify_payment():
    print("\nTesting Isolated Lambda fallback for /api/payment/verify...")
    # Simulate an isolated lambda container where memory and disk don't have the team_code yet,
    # but the frontend sent the fallback metadata
    dummy_code = f"QYRON-27-ISO-{uuid_hex()[:4].upper()}"
    fallback_payload = {
        "team_code": dummy_code,
        "utr_number": "999888777666",
        "order_id": f"order_{dummy_code}",
        "team_name": f"Isolated_{uuid_hex()}",
        "college_name": "IIT Madras",
        "track": "Quantum Algorithms",
        "leader_name": "Isolated Lead",
        "leader_email": f"iso_{uuid_hex()}@example.com",
        "leader_phone": "9876543219",
        "leader_degree": "B.Tech",
        "leader_department": "CSE",
        "leader_gender": "Male"
    }

    res = client.post("/api/payment/verify", data=fallback_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["success"] is True, f"Verify failed: {data}"
    assert data["team_code"] == dummy_code
    print(f"[OK] Isolated Lambda fallback passed! Team {dummy_code} successfully reconstructed and saved.")

def uuid_hex():
    import uuid
    return uuid.uuid4().hex[:6]

def test_team_size_boundaries():
    print("\nTesting Team Size Boundaries (Min 2, Max 4)...")
    base_payload = {
        "team_name": f"SizeTest_{uuid_hex()}",
        "college_name": "Loyola College",
        "track": "Quantum Cryptography",
        "leader_name": "Boundary Lead",
        "leader_phone": "9876543210",
        "leader_email": f"boundary_{uuid_hex()}@example.com",
        "leader_degree": "B.Sc",
        "leader_department": "Mathematics",
        "leader_year": "3rd Year",
        "leader_gender": "Male",
        "utr_number": "123456789012"
    }

    # 1. Test 1 Member total (0 extra members) -> Should FAIL (422)
    p_1 = dict(base_payload, team_name=f"T1_{uuid_hex()}", members=json.dumps([]))
    res_1 = client.post("/api/register", data=p_1)
    assert res_1.status_code == 422, f"Expected 422 for 1 member, got {res_1.status_code}"
    print("[OK] Correctly rejected 1-member team.")

    # 2. Test 2 Members total (1 extra member) -> Should SUCCEED (200)
    p_2 = dict(base_payload, team_name=f"T2_{uuid_hex()}", members=json.dumps([
        {"name": "M2", "email": f"m2_{uuid_hex()}@example.com", "phone": "9876543211", "gender": "Female", "degree": "B.Sc", "department": "Mathematics", "year": "3rd Year"}
    ]))
    res_2 = client.post("/api/register", data=p_2)
    assert res_2.status_code == 200, f"Expected 200 for 2-member team, got {res_2.status_code}: {res_2.text}"
    print("[OK] Correctly accepted 2-member team.")

    # 3. Test 4 Members total (3 extra members) -> Should SUCCEED (200)
    p_4 = dict(base_payload, team_name=f"T4_{uuid_hex()}", members=json.dumps([
        {"name": "M2", "email": f"m2_{uuid_hex()}@example.com", "phone": "9876543211", "gender": "Female", "degree": "B.Sc", "department": "Mathematics", "year": "3rd Year"},
        {"name": "M3", "email": f"m3_{uuid_hex()}@example.com", "phone": "9876543212", "gender": "Male", "degree": "B.Sc", "department": "Mathematics", "year": "3rd Year"},
        {"name": "M4", "email": f"m4_{uuid_hex()}@example.com", "phone": "9876543213", "gender": "Female", "degree": "B.Sc", "department": "Mathematics", "year": "3rd Year"}
    ]))
    res_4 = client.post("/api/register", data=p_4)
    assert res_4.status_code == 200, f"Expected 200 for 4-member team, got {res_4.status_code}: {res_4.text}"
    print("[OK] Correctly accepted 4-member team.")

    # 4. Test 5 Members total (4 extra members) -> Should FAIL (422)
    p_5 = dict(base_payload, team_name=f"T5_{uuid_hex()}", members=json.dumps([
        {"name": "M2", "email": f"m2_{uuid_hex()}@example.com", "phone": "9876543211", "gender": "Female", "degree": "B.Sc", "department": "Mathematics", "year": "3rd Year"},
        {"name": "M3", "email": f"m3_{uuid_hex()}@example.com", "phone": "9876543212", "gender": "Male", "degree": "B.Sc", "department": "Mathematics", "year": "3rd Year"},
        {"name": "M4", "email": f"m4_{uuid_hex()}@example.com", "phone": "9876543213", "gender": "Female", "degree": "B.Sc", "department": "Mathematics", "year": "3rd Year"},
        {"name": "M5", "email": f"m5_{uuid_hex()}@example.com", "phone": "9876543214", "gender": "Male", "degree": "B.Sc", "department": "Mathematics", "year": "3rd Year"}
    ]))
    res_5 = client.post("/api/register", data=p_5)
    assert res_5.status_code == 422, f"Expected 422 for 5-member team, got {res_5.status_code}"
    print("[OK] Correctly rejected 5-member team (exceeds max 4).")

if __name__ == "__main__":
    test_atomic_registration()
    test_isolated_lambda_verify_payment()
    test_team_size_boundaries()
    print("\nALL SERVERLESS RESILIENCE TESTS PASSED!")
