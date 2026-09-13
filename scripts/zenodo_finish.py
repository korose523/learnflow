import os, sys, json, urllib.request, urllib.error, tempfile

TOKEN = os.environ.get("ZENODO_TOKEN")
if not TOKEN:
    print("NO_TOKEN"); sys.exit(2)
API = "https://zenodo.org/api"
DEP = 22719229

def req(method, url, data=None, headers=None):
    h = {"Authorization": f"Bearer {TOKEN}"}
    if headers:
        h.update(headers)
    if isinstance(data, (dict, list)):
        body = json.dumps(data).encode(); h["Content-Type"] = "application/json"
    elif isinstance(data, bytes):
        body = data
    else:
        body = None
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=180) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

# 1. fetch the existing draft deposition (reuse, do not create an orphan)
st, body = req("GET", f"{API}/deposit/depositions/{DEP}")
print("GET_STATUS", st)
if st != 200:
    print("GET_FAILED", body[:800]); sys.exit(1)
dep = json.loads(body)
print("STATE", dep.get("state"))
print("TITLE", dep.get("title") or dep.get("metadata", {}).get("title"))
print("SUBMITTED", dep.get("submitted"))
bucket = dep["links"]["bucket"]
print("BUCKET", bucket)

# 2. ensure the zip is present locally
zip_path = os.path.join(tempfile.gettempdir(), "learnflow-v0.1.0.zip")
if not os.path.exists(zip_path):
    print("REDOWNLOADING")
    urllib.request.urlretrieve("https://github.com/korose523/learnflow/archive/refs/tags/v0.1.0.zip", zip_path)
print("ZIP_BYTES", os.path.getsize(zip_path))

# 3. upload with the REQUIRED Content-Type
with open(zip_path, "rb") as f:
    filedata = f.read()
st, body = req("PUT", f"{bucket}/learnflow-v0.1.0.zip", data=filedata,
               headers={"Content-Type": "application/octet-stream"})
print("UPLOAD_STATUS", st)
if st not in (200, 201):
    print("UPLOAD_FAILED", body[:800]); sys.exit(1)
print("UPLOAD_OK")

# 4. publish -> mint DOI
st, body = req("POST", f"{API}/deposit/depositions/{DEP}/actions/publish", data={})
print("PUBLISH_STATUS", st)
if st not in (200, 202):
    print("PUBLISH_FAILED", body[:800]); sys.exit(1)
pub = json.loads(body)
print("DOI", pub.get("doi"))
print("CONCEPTDOI", pub.get("conceptdoi"))
print("RECORD_URL", pub.get("links", {}).get("html"))
print("DONE")
