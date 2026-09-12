"""
Verification script for CivicVoice backend API — Comprehensive Suite
"""
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_all():
    print("--- 1. Testing GET /api/health ---")
    res = client.get("/api/health")
    assert res.status_code == 200, res.text
    data = res.json()
    print("Health response:", data)
    assert data["schemes_loaded"] == 20, f"Expected 20 schemes, found {data['schemes_loaded']}"

    print("\n--- 2. Testing GET /api/schemes ---")
    s_res = client.get("/api/schemes")
    assert s_res.status_code == 200
    assert s_res.json()["count"] == 20
    print("All 20 schemes loaded successfully!")

    print("\n--- 3. Testing POST /api/process (Farmer Citizen) ---")
    phone = "9876543210"
    p1 = client.post(
        "/api/process",
        json={
            "phone": phone,
            "text": "I am a 42 year old farmer living in a rural village with my 7 year old daughter."
        }
    )
    assert p1.status_code == 200, p1.text
    d1 = p1.json()
    print("Profile extracted:", d1["profile"])
    print("Extraction source:", d1.get("extraction_source"))
    print("Matches count:", len(d1["matched_schemes"]))
    assert "extraction_source" in d1

    # Farmer scheme (PM-KISAN) should match
    pm_kisan = next((s for s in d1["matched_schemes"] if s["id"] == "pm_kisan"), None)
    assert pm_kisan is not None, "PM-KISAN should be surfaced"
    print("PM-KISAN status:", pm_kisan["status"])

    # Sukanya Samriddhi should match because has_daughter=True, daughter_age=7 <= 10
    sukanya = next((s for s in d1["matched_schemes"] if s["id"] == "sukanya_samriddhi"), None)
    assert sukanya is not None, "Sukanya Samriddhi should be surfaced"
    print("Sukanya Samriddhi status:", sukanya["status"])

    print("\n--- 4. Testing Memory Persistence across calls ---")
    p2 = client.post(
        "/api/process",
        json={
            "phone": phone,
            "text": "We belong to BPL category and our house is a kutcha mud house. We have an active bank account."
        }
    )
    assert p2.status_code == 200
    d2 = p2.json()
    assert d2["is_returning_citizen"] is True, "Must identify returning citizen"
    assert d2["profile"]["occupation"] == "farmer", "Memory failed: lost farmer occupation"
    assert d2["profile"]["income_bracket"] == "bpl", "New fact income_bracket not merged"
    assert d2["profile"]["has_bank_account"] is True, "Bank account not merged"
    print("Merged profile correctly preserved old & new facts:", d2["profile"])

    print("\n--- 5. Testing Artisan Profile -> PM Vishwakarma ---")
    artisan_phone = "9844001122"
    p_art = client.post(
        "/api/process",
        json={
            "phone": artisan_phone,
            "text": "I am a 35 year old carpenter and traditional wood craftsman with a bank account."
        }
    )
    assert p_art.status_code == 200
    d_art = p_art.json()
    vishwakarma = next((s for s in d_art["matched_schemes"] if s["id"] == "pm_vishwakarma"), None)
    assert vishwakarma is not None, "PM Vishwakarma should match artisan profile"
    print("PM Vishwakarma matched:", vishwakarma["status"], "Benefit:", vishwakarma["benefit"][:60])

    print("\n--- 6. Testing Street Vendor Profile -> PM SVANidhi ---")
    vendor_phone = "9822334455"
    p_vend = client.post(
        "/api/process",
        json={
            "phone": vendor_phone,
            "text": "I am a street vendor running a fruit cart in the city with a bank savings account."
        }
    )
    assert p_vend.status_code == 200
    d_vend = p_vend.json()
    svanidhi = next((s for s in d_vend["matched_schemes"] if s["id"] == "pm_svanidhi"), None)
    assert svanidhi is not None, "PM SVANidhi should match street vendor profile"
    print("PM SVANidhi matched:", svanidhi["status"])

    print("\n--- 7. Testing POST /api/advisor-summary ---")
    adv_res = client.post("/api/advisor-summary", json={"phone": phone, "language": "en-IN"})
    assert adv_res.status_code == 200
    adv_data = adv_res.json()
    print("Advisor summary:", adv_data["summary_text"][:120], "...")
    assert adv_data["total_confirmed"] >= 1

    print("\n--- 8. Testing POST /api/chat ---")
    chat_res = client.post(
        "/api/chat",
        json={"phone": phone, "message": "What documents do I need for PM-KISAN?", "language": "en-IN"}
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    print("Chat Assistant response:", chat_data["reply"][:120], "...")
    assert len(chat_data["reply"]) > 10

    print("\n--- 9. Testing POST /api/followup ---")
    f_res = client.post("/api/followup", json={"phone": phone, "target_lang": "en-IN"})
    assert f_res.status_code == 200
    f_data = f_res.json()
    print("Follow-up response:", f_data)

    print("\n--- 10. Testing GET /api/draft/pdf (ReportLab generation) ---")
    pdf_res = client.get(f"/api/draft/pdf?phone={phone}&scheme_id=pm_kisan")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    content = pdf_res.content
    assert content.startswith(b"%PDF"), "Response is not a valid PDF file"
    print(f"PDF generated successfully! Size: {len(content)} bytes")

    print("\n--- 11. Testing POST /api/translate ---")
    t_res = client.post(
        "/api/translate",
        json={"text": "You qualify for PM-KISAN. Documents needed: Aadhaar card", "target_lang": "hi-IN"}
    )
    assert t_res.status_code == 200
    print("Translation response:", json.dumps(t_res.json(), ensure_ascii=True))

    print("\n--- 12. Testing GET /api/stats ---")
    stats_res = client.get("/api/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    print("Aggregate stats:", stats_data)
    assert stats_data["total_available_schemes"] == 20

    print("\n>>> ALL 12 BACKEND TESTS PASSED CLEANLY! <<<")

if __name__ == "__main__":
    test_all()
