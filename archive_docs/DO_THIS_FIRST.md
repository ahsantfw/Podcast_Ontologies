# 🎯 DO THIS FIRST (Before Asking Teacher)

## Step-by-Step Guide

### ⚡ STEP 1: Test Everything Locally (30 minutes)

**This is the MOST IMPORTANT step!**

```bash
# 1. Navigate to project
cd /path/to/ontology_production_v1

# 2. Test Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Open new terminal, test:
curl http://localhost:8000/api/v1/health
# Should return: {"status": "healthy"}
```

```bash
# 3. Test Frontend (new terminal)
cd frontend
npm install
npm run dev

# Open browser: http://localhost:5173
# Should show the chat interface
```

**✅ CHECK:** Does everything work? If YES → continue. If NO → fix errors first!

---

### ⚡ STEP 2: Check Required Files (5 minutes)

Verify these files exist:

```bash
# Check from project root
ls backend/Dockerfile          # ✅ Should exist
ls deploy-gcp.sh               # ✅ Should exist
ls firebase.json               # ✅ Should exist
ls .env                        # ✅ Should have Neo4j, OpenAI keys
```

**✅ CHECK:** All files present? If YES → continue. If NO → create missing files!

---

### ⚡ STEP 3: Prepare Info for Teacher (5 minutes)

Create a note with:

```
I need from teacher:
1. GCP project access (project name: podcast-intelligence)
   OR give me access to existing project

2. Neo4j credentials (check if in .env file):
   - NEO4J_URI: ________________
   - NEO4J_PASSWORD: ________________

3. OpenAI API Key: 
   - Use mine? OR teacher's?

My status:
- ✅ Tested locally (works)
- ✅ All files ready
- ✅ Ready to deploy
```

---

### ⚡ STEP 4: Send Message to Teacher

**Copy from:** `MESSAGE_TO_TEACHER.md`

Or send this:

```
Hi [Teacher],

I've tested the project locally and it works. 
I'm ready to deploy to GCP.

I need:
1. GCP project access (or create: podcast-intelligence)
2. Neo4j credentials (if not in .env)
3. Confirm OpenAI key usage

Ready when you are!

Thanks!
```

---

## 🚨 If Something Fails in STEP 1

### Backend won't start?
```bash
# Check .env file exists
ls .env

# Check Neo4j is accessible
# (Try connecting with credentials from .env)

# Check dependencies
pip install --upgrade -r backend/requirements.txt
```

### Frontend won't start?
```bash
# Check Node.js version (need 18+)
node --version

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Qdrant connection fails?
```bash
# Check if Qdrant is running locally
curl http://localhost:6333/health

# If not running:
docker run -d -p 6333:6333 qdrant/qdrant
```

---

## ✅ Checklist: Am I Ready?

Before telling teacher, check:

- [ ] Backend runs locally without errors
- [ ] Frontend runs locally without errors  
- [ ] Can access API at `http://localhost:8000/api/v1/health`
- [ ] All deployment files exist (Dockerfile, deploy script, firebase.json)
- [ ] .env file has Neo4j credentials
- [ ] Know what GCP project name you want

**If ALL checked ✅ → Tell teacher you're ready!**

---

## 📋 After Teacher Gives Access

### Step 1: Login to GCP
```bash
gcloud auth login
```

### Step 2: Set Project
```bash
gcloud config set project <project-id-from-teacher>
```

### Step 3: Run Deployment
```bash
./deploy-gcp.sh
```

---

**🎯 REMEMBER: Test locally FIRST, then ask teacher!**

