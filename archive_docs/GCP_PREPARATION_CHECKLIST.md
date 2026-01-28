# 📋 GCP Deployment Preparation Checklist

## 🎯 Situation

- **Project location**: Teacher's laptop
- **Your location**: Local machine
- **Qdrant**: Running locally
- **Neo4j**: Cloud (connection in .env)
- **Next step**: Get GCP access from teacher

---

## ✅ STEP 1: Prepare Everything on YOUR Local Machine (DO THIS FIRST)

### 1.1 Get Project Files from Teacher

```bash
# Option A: Git clone (if teacher has repo)
git clone <teacher-repo-url>

# Option B: Get files via USB/Network share
# Copy entire project folder to your machine

# Option C: Ask teacher to zip and share project folder
```

### 1.2 Check Required Files

Verify you have:

- [ ] `backend/` folder with `Dockerfile`
- [ ] `frontend/` folder with `package.json`
- [ ] `.env` file (with Neo4j credentials)
- [ ] `deploy-gcp.sh` script
- [ ] `firebase.json`

### 1.3 Test Locally First (IMPORTANT!)

```bash
# Test backend
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Test frontend (in new terminal)
cd frontend
npm install
npm run dev
```

**If local tests fail, fix them BEFORE deploying to GCP!**

### 1.4 Prepare Environment Variables

Create a list of what you'll need:

- [ ] `NEO4J_URI` - From teacher's .env
- [ ] `NEO4J_USER` - From teacher's .env
- [ ] `NEO4J_PASSWORD` - From teacher's .env
- [ ] `OPENAI_API_KEY` - Your key or teacher's
- [ ] `QDRANT_URL` - Will be set after Qdrant deploys

### 1.5 Prepare Deployment Info for Teacher

Create a document with:

- [ ] GCP project name you want: `podcast-intelligence`
- [ ] Region preference: `us-central1` (or ask teacher)
- [ ] Estimated resources:
  - Backend: 2GB RAM, 2 CPU
  - Qdrant: 4GB RAM, 2 CPU
  - Frontend: Free (Firebase)

---

## ✅ STEP 2: Tell Your Teacher (After Step 1)

### Email/Message Template:

```
Subject: GCP Deployment Preparation - Ready for Access

Hi [Teacher],

I've prepared the project for GCP deployment:

✅ Completed:
1. Tested project locally (backend + frontend working)
2. Prepared all configuration files (Dockerfile, deploy script)
3. Listed required environment variables (Neo4j, OpenAI)

📋 What I Need:
1. GCP project access (or create project: "podcast-intelligence")
2. Your Neo4j connection details (for .env)
3. Confirmation: Should I use my OpenAI key or yours?

🚀 Next Steps (after access):
1. Deploy Qdrant to Cloud Run
2. Deploy Backend API to Cloud Run  
3. Deploy Frontend to Firebase Hosting

Estimated time: 30-60 minutes after I get access.

Ready when you are!
```

---

## ✅ STEP 3: After Teacher Gives Access

### 3.1 Verify Access

```bash
# Login to GCP
gcloud auth login

# List projects
gcloud projects list

# Set project (teacher will tell you the project ID)
gcloud config set project <project-id-from-teacher>
```

### 3.2 Get Missing Information

Ask teacher for:

- [ ] GCP project ID
- [ ] Neo4j URI (if not in .env)
- [ ] Neo4j password (if not in .env)
- [ ] Which OpenAI key to use

### 3.3 Run Deployment

```bash
# Make script executable
chmod +x deploy-gcp.sh

# Run deployment (will ask for secrets interactively)
./deploy-gcp.sh
```

---

## 🔧 What to Do RIGHT NOW (Most Important)

### Priority 1: Test Locally ✅

```bash
# 1. Get project from teacher (or work on your local copy)
# 2. Test backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

# 3. Test frontend  
cd frontend
npm install
npm run dev

# 4. Verify everything works!
```

### Priority 2: Prepare Deployment Files ✅

- [ ] Verify `backend/Dockerfile` exists
- [ ] Verify `firebase.json` exists
- [ ] Verify `deploy-gcp.sh` is executable

### Priority 3: Document What You Need ✅

Create a file: `DEPLOYMENT_INFO.txt` with:

```
Needed from Teacher:
1. GCP project access
2. Neo4j URI: [ask teacher]
3. Neo4j password: [ask teacher]  
4. OpenAI API key: [your own or teacher's?]

My Info:
- Local machine ready: ✅
- Tests passed: ✅
- Ready to deploy: ✅
```

---

## 🚨 Common Issues & Solutions

### Issue: "Project not found"

**Solution**: Teacher needs to create project or give you access

```bash
# Teacher runs:
gcloud projects create podcast-intelligence
gcloud projects add-iam-policy-binding podcast-intelligence \
  --member=user:your-email@gmail.com \
  --role=roles/owner
```

### Issue: "Permission denied"

**Solution**: Teacher needs to give you IAM permissions

```bash
# Teacher runs:
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:your-email@gmail.com \
  --role=roles/run.admin
gcloud projects add-iam-policy-binding <project-id> \
  --member=user:your-email@gmail.com \
  --role=roles/secretmanager.admin
```

### Issue: "Neo4j connection failed"

**Solution**: Verify .env has correct Neo4j credentials

---

## 📝 Checklist Summary

**Before Asking Teacher:**

- [ ] Project works locally
- [ ] All files present (Dockerfile, deploy script, etc.)
- [ ] Know what environment variables you need
- [ ] Know what GCP resources you need

**Ask Teacher For:**

- [ ] GCP project access OR project name to create
- [ ] Neo4j credentials (if not already shared)
- [ ] Confirmation on OpenAI key

**After Teacher Gives Access:**

- [ ] Run `gcloud auth login`
- [ ] Set project: `gcloud config set project <id>`
- [ ] Run `./deploy-gcp.sh`

---

**🎯 FIRST THING TO DO RIGHT NOW:**

1. **Test locally** - Make sure backend + frontend work
2. **Check files** - Verify Dockerfile, deploy script exist
3. **Document needs** - List what you need from teacher
4. **Send message** - Tell teacher you're ready

**Time needed:** 30 minutes to prepare, then wait for teacher's access
