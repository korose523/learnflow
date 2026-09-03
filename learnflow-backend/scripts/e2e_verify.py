#!/usr/bin/env python3
"""LearnFlow 线上端到端验证脚本（仅使用标准库）"""
import json
import ssl
import sys
from urllib import request, error, parse

BASE_URL = "https://learnflow-api-272550-6-1256129125.sh.run.tcloudbase.com/api/v1"
TIMEOUT = 30

USERS = {
    "student": {"username": "student@learnflow.com", "password": "Student123!"},
    "teacher": {"username": "teacher@learnflow.com", "password": "Teacher123!"},
    "parent": {"username": "parent@learnflow.com", "password": "Parent123!"},
    "admin": {"username": "admin@learnflow.com", "password": "Admin1234!"},
}

results = []

# 允许自签名/CloudBase 证书（生产环境不建议）
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


def log(name, status, detail=None, error=None):
    results.append({"name": name, "status": status, "detail": detail, "error": error})
    print(f"[{'PASS' if status else 'FAIL'}] {name}")
    if detail:
        print(f"  Detail: {detail}")
    if error:
        print(f"  Error: {error}")


def http_call(method, path, token=None, body=None, json_body=None, form_body=None):
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif form_body is not None:
        data = parse.urlencode(form_body).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = body.encode("utf-8") if isinstance(body, str) else body

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=TIMEOUT, context=SSL_CONTEXT) as resp:
            return resp.status, resp.read().decode("utf-8")
    except error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return None, str(e)


def login(role):
    code, text = http_call("POST", "/auth/login", form_body=USERS[role])
    if code != 200:
        return None, f"HTTP {code}: {text[:200]}"
    try:
        data = json.loads(text)
    except Exception as e:
        return None, f"JSON parse error: {e}"
    if "access_token" not in data:
        return None, f"No access_token: {data}"
    return data["access_token"], None


def get(path, token=None):
    return http_call("GET", path, token=token)


def post(path, token=None, json_body=None):
    return http_call("POST", path, token=token, json_body=json_body)


def main():
    student_id = None
    task_id = None

    # 1. Student login + dashboard has_pet
    token, err = login("student")
    if err:
        log("Student login", False, error=err)
        return results
    log("Student login", True, detail="token obtained")

    code, text = get("/auth/me", token)
    if code != 200:
        log("Student /auth/me", False, error=f"HTTP {code}: {text[:200]}")
    else:
        try:
            me_data = json.loads(text)
            student_id = me_data.get("id")
            log("Student /auth/me", True, detail=f"role={me_data.get('role')}, id={student_id}")
        except Exception as e:
            log("Student /auth/me", False, error=f"JSON parse: {e}")

    code, text = get("/student/dashboard", token)
    if code != 200:
        log("Student dashboard", False, error=f"HTTP {code}: {text[:200]}")
    else:
        try:
            dash_data = json.loads(text)
            has_pet = dash_data.get("has_pet")
            log("Student dashboard has_pet", bool(has_pet), detail=f"has_pet={has_pet}, keys={list(dash_data.keys())}")
        except Exception as e:
            log("Student dashboard", False, error=f"JSON parse: {e}")

    # 2. /student/next-task contains bkt and learning_tip
    code, text = get("/student/next-task", token)
    if code != 200:
        log("Student /student/next-task", False, error=f"HTTP {code}: {text[:200]}")
    else:
        try:
            nt_data = json.loads(text)
            has_bkt = any(k in nt_data for k in ["bkt", "bkt_probability", "p_know", "p_knows"])
            has_tip = bool(nt_data.get("learning_tip"))
            log("Student /student/next-task bkt", has_bkt, detail=f"keys={list(nt_data.keys())}")
            log("Student /student/next-task learning_tip", has_tip, detail=f"learning_tip={nt_data.get('learning_tip')}")
            task_id = nt_data.get("task_id") or nt_data.get("id")
        except Exception as e:
            log("Student /student/next-task", False, error=f"JSON parse: {e}")

    # 3. /student/submit-answer creates SpacedReview
    if task_id:
        code, text = post("/student/submit-answer", token, json_body={"task_id": task_id, "answer": "1", "time_spent": 5, "hints_used": 0})
        if code != 200:
            log("Student /student/submit-answer", False, error=f"HTTP {code}: {text[:200]}")
        else:
            try:
                ans_data = json.loads(text)
                has_review = bool(
                    ans_data.get("spaced_review")
                    or ans_data.get("next_review")
                    or ans_data.get("review_scheduled")
                    or ans_data.get("due_at")
                )
                log("Student /student/submit-answer SpacedReview", has_review, detail=f"keys={list(ans_data.keys())}")
            except Exception as e:
                log("Student /student/submit-answer", False, error=f"JSON parse: {e}")

    # 4. Teacher login + /teacher/ai/student-analysis/{student_id} not 500
    t_token, err = login("teacher")
    if err:
        log("Teacher login", False, error=err)
    else:
        log("Teacher login", True)
        sid = student_id if student_id else "1"
        code, text = get(f"/teacher/ai/student-analysis/{sid}", t_token)
        if code == 200:
            try:
                ai_data = json.loads(text)
                log(f"Teacher AI analysis student_id={sid}", True, detail=f"keys={list(ai_data.keys())}")
            except Exception as e:
                log(f"Teacher AI analysis student_id={sid}", False, error=f"JSON parse: {e}")
        else:
            log(f"Teacher AI analysis student_id={sid}", False, error=f"HTTP {code}: {text[:200]}")

    # 5. Parent login + child summary not hardcoded
    p_token, err = login("parent")
    if err:
        log("Parent login", False, error=err)
    else:
        log("Parent login", True)
        sid = student_id if student_id else "1"
        code, text = get(f"/parent/child/{sid}/summary", p_token)
        if code == 200:
            try:
                ps_data = json.loads(text)
                not_hardcoded = bool(
                    ps_data.get("student_name")
                    and ps_data.get("student_name") != "Demo Student"
                    and ps_data.get("overall_mastery") is not None
                    and ps_data.get("weekly_attempts") is not None
                )
                log(f"Parent child summary student_id={sid}", not_hardcoded, detail=f"keys={list(ps_data.keys())}")
            except Exception as e:
                log(f"Parent child summary student_id={sid}", False, error=f"JSON parse: {e}")
        else:
            log(f"Parent child summary student_id={sid}", False, error=f"HTTP {code}: {text[:200]}")

    # 6. Admin login + pending tasks list
    a_token, err = login("admin")
    if err:
        log("Admin login", False, error=err)
    else:
        log("Admin login", True)
        code, text = get("/admin/pending-tasks", a_token)
        if code == 200:
            try:
                pt_data = json.loads(text)
                count = len(pt_data) if isinstance(pt_data, list) else "N/A"
                log("Admin /admin/pending-tasks", True, detail=f"count={count}")
            except Exception as e:
                log("Admin /admin/pending-tasks", False, error=f"JSON parse: {e}")
        else:
            log("Admin /admin/pending-tasks", False, error=f"HTTP {code}: {text[:200]}")

    # 7. Gamification pages accessible (200)
    pages = [
        ("/student/gamification/streak", "streak"),
        ("/student/gamification/leaderboard", "leaderboard"),
        ("/student/gamification/skill-tree", "skill-tree"),
        ("/student/gamification/team", "team"),
    ]
    for path, name in pages:
        code, text = get(path, token)
        log(f"Student gamification /{name}", code == 200, detail=f"HTTP {code}")

    return results


if __name__ == "__main__":
    main()
    passed = sum(1 for r in results if r["status"])
    failed = sum(1 for r in results if not r["status"])
    print(f"\nE2E Summary: passed={passed}, failed={failed}")
    sys.exit(0 if failed == 0 else 1)
