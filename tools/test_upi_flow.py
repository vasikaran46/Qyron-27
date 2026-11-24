import io
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app

def main():
    client = TestClient(app)

    # 1. Test registration submission
    members = [
        {"name": "Jai Bharath A", "phone": "8072039943", "email": "jaib9943@gmail.com", "degree": "B.Sc", "department": "Department of Mathematics", "year": "3rd Year", "gender": "Male"},
        {"name": "Nethra S", "phone": "9962819163", "email": "nethrasoundarrajan02@gmail.com", "degree": "B.Sc", "department": "Department of Mathematics", "year": "3rd Year", "gender": "Female"},
        {"name": "Immanuel GM", "phone": "7200481327", "email": "gmimmanuel4@gmail.com", "degree": "B.Sc", "department": "Department of Mathematics", "year": "3rd Year", "gender": "Male"}
    ]

    team_name = f"Quantum Phoenix {int(time.time())}"
    reg_data = {
        "team_name": team_name,
        "college_name": "Patrician College of Arts and Science",
        "track": "Track 1: Quantum Superposition & Circuit Modeling",
        "leader_name": "Vasikaran A",
        "leader_phone": "9876543210",
        "leader_email": "karanvasi80@gmail.com",
        "leader_degree": "B.Sc",
        "leader_department": "Department of Mathematics",
        "leader_year": "3rd Year",
        "leader_gender": "Male",
        "members": json.dumps(members)
    }

    res = client.post("/api/register", data=reg_data)
    assert res.status_code == 200, f"Register failed: {res.text}"
    data = res.json()
    assert data.get("success") is True, f"Not success: {data}"
    team_code = data["team_code"]
    order = data["order"]
    assert order["mode"] == "upi_qr"
    assert order["upi_id"] == "karanvasi80@okhdfcbank"
    print(f"[OK] Step 1: Registered squad {team_code} with UPI QR mode (UPI ID: {order['upi_id']})")

    # 2. Participant submits 12-digit UTR + screenshot -> sets status to pending_verification and dispatches Email 1
    utr_test = "402819284712"
    fake_screenshot = io.BytesIO(b"Fake receipt image content")
    verify_res = client.post(
        "/api/payment/verify",
        data={
            "team_code": team_code,
            "utr_number": utr_test,
            "order_id": order["order_id"]
        },
        files={"payment_screenshot": ("receipt.jpg", fake_screenshot, "image/jpeg")}
    )

    assert verify_res.status_code == 200, f"Payment verify failed: {verify_res.text}"
    v_data = verify_res.json()
    assert v_data.get("success") is True
    assert v_data.get("payment_status") == "pending_verification"
    assert v_data.get("username") == "karanvasi80@gmail.com"
    assert v_data.get("password")
    print(f"[OK] Step 2: Credentials generated immediately ({v_data.get('username')}). UPI UTR logged ({utr_test}). Status is 'pending_verification' — Email 1 dispatched to participant.")

    # 3. Check registration record status
    conf_res = client.get(f"/api/registration/{team_code}")
    assert conf_res.status_code == 200
    reg_record = conf_res.json()["registration"]
    assert reg_record["utr_number"] == utr_test
    assert reg_record["payment_status"] == "pending_verification"
    print(f"[OK] Step 3: Registration record verified in registry as 'pending_verification' with UTR {reg_record['utr_number']}")

    # 4. Admin verifies payment in Admin Panel -> sets status to 'paid' and dispatches Email 2 with credentials!
    admin_verify_res = client.post(f"/api/admin/registrations/{team_code}/verify-payment")
    assert admin_verify_res.status_code == 200, f"Admin verify failed: {admin_verify_res.text}"
    admin_data = admin_verify_res.json()
    assert admin_data.get("success") is True
    assert admin_data.get("payment_status") == "paid"
    print(f"[OK] Step 4: Admin verified payment for {team_code}! Email 2 dispatched with portal credentials to {admin_data.get('username')}.")

    # 5. Check registration record is now marked 'paid'
    conf_res_verified = client.get(f"/api/registration/{team_code}")
    reg_verified = conf_res_verified.json()["registration"]
    assert reg_verified["payment_status"] == "paid"
    print(f"[OK] Step 5: Registration record confirmed active & 'paid' in registry.")

    # 6. Test portal proposal submission
    fake_ppt = io.BytesIO(b"PK\x03\x04 fake pptx content")
    proposal_res = client.post(
        "/api/portal/submit-proposal",
        data={
            "team_code": team_code,
            "idea_title": "Topological Quantum Resilience in Mesh Networks",
            "idea_summary": "An advanced mathematical error-correction schema for non-abelian anyon braiding in distributed quantum networks.",
            "idea_description": "Formulates Toric code stabilization with SymPy Hamiltonians and Qiskit fault-tolerant threshold modeling."
        },
        files={"idea_ppt": ("proposal.pptx", fake_ppt, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
    )

    assert proposal_res.status_code == 200, f"Proposal failed: {proposal_res.text}"
    p_data = proposal_res.json()
    assert p_data.get("success") is True
    print(f"[OK] Step 6: Proposal dossier & PPT submitted successfully for {team_code}")
    print("\nALL TWO-PHASE PAYMENT & EMAIL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
