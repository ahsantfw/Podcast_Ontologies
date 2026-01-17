# ⚡ Quick Start - Do This FIRST

## 🎯 Priority 1: Test Locally (MOST IMPORTANT!)

```bash
# Test Backend
cd backend
python -m uvicorn app.main:app --port 8000

# In another terminal, test:
curl http://localhost:8000/api/v1/health
# ✅ Should see: {"status": "healthy"}

# Test Frontend  
cd frontend
npm install
npm run dev
# ✅ Should open at http://localhost:5173
```

**✅ If both work → Continue to Step 2**
**❌ If errors → Fix them first!**

---

## 🎯 Priority 2: Check Files

```bash
# From project root, verify:
ls backend/Dockerfile  # ✅ Must exist
ls deploy-gcp.sh       # ✅ Must exist  
ls firebase.json       # ✅ Must exist
ls .env                # ✅ Should have Neo4j, OpenAI
```

**✅ All files exist → Continue to Step 3**

---

## 🎯 Priority 3: Tell Teacher

**Send this message:**

```
Hi [Teacher],

I've tested the project locally - it works!

I need:
1. GCP project access (project: podcast-intelligence)
2. Neo4j credentials (if not in .env)

Ready to deploy!

Thanks!
```

**✅ Message sent → Wait for teacher's response**

---

## 📝 Summary

**DO FIRST:**
1. ✅ Test locally (backend + frontend)
2. ✅ Check all files exist
3. ✅ Tell teacher you're ready

**AFTER TEACHER GIVES ACCESS:**
1. `gcloud auth login`
2. `gcloud config set project <id>`
3. `./deploy-gcp.sh`

---

**Time needed: 30 minutes to prepare, then wait for teacher**

