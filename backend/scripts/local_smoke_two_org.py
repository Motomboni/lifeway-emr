"""
Local smoke test: clinic signup, login, patient/visit, two-org isolation.
Run with server up: python manage.py runserver
Usage: python scripts/local_smoke_two_org.py
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
SUFFIX = str(int(time.time()))[-8:]


def req(method, path, body=None, token=None, org_id=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if org_id is not None:
        headers["X-Organization-Id"] = str(org_id)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw) if raw else {"detail": e.reason}
        except json.JSONDecodeError:
            payload = {"detail": raw[:200]}
        return e.code, payload


def ok(cond, msg):
    if cond:
        print(f"  PASS: {msg}")
        return True
    print(f"  FAIL: {msg}")
    return False


def main():
    failures = 0
    slug_a = f"smoke-a-{SUFFIX}"
    slug_b = f"smoke-b-{SUFFIX}"
    user_a = f"owner_a_{SUFFIX}"
    user_b = f"owner_b_{SUFFIX}"

    print("=== Step 1: Local smoke test ===\n")

    print("1. Clinic signup (Org A)")
    code, data = req(
        "POST",
        "/organizations/signup/",
        {
            "name": f"Smoke Clinic A {SUFFIX}",
            "slug": slug_a,
            "username": user_a,
            "password": "SmokeTest123!",
            "first_name": "Owner",
            "last_name": "A",
        },
    )
    if not ok(code == 201, f"signup -> {code} {data.get('detail', data.get('message', ''))}"):
        failures += 1
        print("\nAborting: signup failed. Is ENABLE_ORG_SIGNUP=true and server running?")
        return 1
    org_a_id = data["organization"]["id"]

    print("2. Login Org A")
    code, data = req("POST", "/auth/login/", {"username": user_a, "password": "SmokeTest123!"})
    if not ok(code == 200 and "access" in data, f"login -> {code}"):
        failures += 1
        return 1
    token_a = data["access"]

    patient_a_id = None
    visit_a_id = None

    print("3. Create patient in Org A")
    code, pdata = req(
        "POST",
        "/patients/",
        {
            "first_name": "Alice",
            "last_name": "Smoke",
            "gender": "FEMALE",
        },
        token=token_a,
        org_id=org_a_id,
    )
    if not ok(code in (200, 201), f"create patient -> {code} {pdata.get('detail', pdata.get('error', ''))}"):
        failures += 1
    else:
        patient_a_id = pdata.get("patient", {}).get("id")

        print("4. Create visit for patient")
        code, vdata = req(
            "POST",
            "/visits/",
            {"patient": patient_a_id},
            token=token_a,
            org_id=org_a_id,
        )
        if not ok(code in (200, 201), f"create visit -> {code} {vdata}"):
            failures += 1
        else:
            visit_a_id = vdata.get("id")

            print("5. List patients (Org A sees own)")
            code, listed = req("GET", "/patients/", token=token_a, org_id=org_a_id)
            ids = set()
            if isinstance(listed, list):
                ids = {p["id"] for p in listed}
            elif isinstance(listed, dict) and "results" in listed:
                ids = {p["id"] for p in listed["results"]}
            if not ok(code == 200 and patient_a_id in ids, "Org A lists own patient"):
                failures += 1

    print("\n=== Step 2: Two-org isolation (local, production-like flags) ===\n")

    print("6. Clinic signup (Org B)")
    code, data = req(
        "POST",
        "/organizations/signup/",
        {
            "name": f"Smoke Clinic B {SUFFIX}",
            "slug": slug_b,
            "username": user_b,
            "password": "SmokeTest123!",
            "first_name": "Owner",
            "last_name": "B",
        },
    )
    if not ok(code == 201, f"signup B -> {code}"):
        failures += 1
        return 1
    org_b_id = data["organization"]["id"]

    print("7. Login Org B")
    code, data = req("POST", "/auth/login/", {"username": user_b, "password": "SmokeTest123!"})
    if not ok(code == 200, f"login B -> {code}"):
        failures += 1
        return 1
    token_b = data["access"]

    if patient_a_id:
        print("8. Org B cannot retrieve Org A patient")
        code, _ = req("GET", f"/patients/{patient_a_id}/", token=token_b, org_id=org_b_id)
        if not ok(code == 404, f"cross-tenant patient -> {code} (expected 404)"):
            failures += 1

        if visit_a_id:
            print("9. Org B cannot retrieve Org A visit")
            code, _ = req("GET", f"/visits/{visit_a_id}/", token=token_b, org_id=org_b_id)
            if not ok(code == 404, f"cross-tenant visit -> {code} (expected 404)"):
                failures += 1

            print("11. Cross-tenant consultation blocked")
            code, _ = req(
                "GET",
                f"/visits/{visit_a_id}/consultation/",
                token=token_b,
                org_id=org_b_id,
            )
            if not ok(code in (403, 404), f"consultation cross-tenant -> {code} (expected 403/404)"):
                failures += 1
    else:
        print("8-11. SKIP isolation checks (no patient/visit from step 3)")
        failures += 1

    print("10. Org B patient list excludes Org A patient")
    code, listed = req("GET", "/patients/", token=token_b, org_id=org_b_id)
    ids = set()
    if isinstance(listed, list):
        ids = {p["id"] for p in listed}
    elif isinstance(listed, dict) and "results" in listed:
        ids = {p["id"] for p in listed["results"]}
    if patient_a_id:
        if not ok(code == 200 and patient_a_id not in ids, "Org B list excludes Org A patient"):
            failures += 1
    elif not ok(code == 200, f"list patients B -> {code}"):
        failures += 1

    if patient_a_id:
        print("12. Wrong org header cannot access Org A patient")
        code, _ = req(
            "GET", f"/patients/{patient_a_id}/", token=token_a, org_id=org_b_id
        )
        if not ok(code == 404, f"wrong-header patient -> {code} (expected 404)"):
            failures += 1
        if visit_a_id:
            print("13. Wrong org header cannot access Org A visit")
            code, _ = req(
                "GET", f"/visits/{visit_a_id}/", token=token_a, org_id=org_b_id
            )
            if not ok(code == 404, f"wrong-header visit -> {code} (expected 404)"):
                failures += 1

    print("\n=== Summary ===")
    if failures:
        print(f"FAILED: {failures} check(s)")
        return 1
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
