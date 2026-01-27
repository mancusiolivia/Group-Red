# Setup Guide for New Developers

This guide walks you through setting up the Essay Testing System from scratch after cloning from git.

## Prerequisites

- Python 3.8 or higher
- Git
- Access to Together.ai API key (contact Olivia if you need one)

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Capstone
```

### 2. Install Python Dependencies

```bash
pip install -r server/requirements.txt
```

**Note:** On some systems, you may need to use `pip3` instead of `pip`.

### 3. Set Up Environment Variables

Create a `.env` file in the project root directory:

```bash
# Windows (PowerShell)
New-Item -Path .env -ItemType File

# Linux/Mac
touch .env
```

Add your Together.ai API key to the `.env` file:

```
TOGETHER_AI_API_KEY=your_api_key_here
```

**⚠️ Important:** 
- The `.env` file is already in `.gitignore`, so it won't be committed to git
- Each developer needs their own API key
- Contact Olivia if you need an API key

### 4. Initialize Database and Create Login Users

**This is a critical step!** The database will auto-create on startup, but you need to run the seed script to create login users:

```bash
python server/database/seed_data.py
```

**Or on some systems:**
```bash
python3 server/database/seed_data.py
```

This will create the following test accounts:

| Username | Password | Type |
|----------|----------|------|
| `admin` | `admin123` | Instructor |
| `student1` | `password123` | Student |
| `student2` | `password123` | Student |
| `testuser` | `test123` | Student |

**Note:** The seed script is idempotent - it's safe to run multiple times. It will only create users that don't already exist.

### 5. Start the Server

**Option 1 (Recommended):** Use the run script:
```bash
python run_server.py
```

**Option 2:** Run main.py directly:
```bash
python server/main.py
```

**Option 3:** Use uvicorn directly:
```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### 6. Access the Application

Open your web browser and navigate to:
```
http://localhost:8000
```

You should see the login page. Use one of the test accounts created in step 4 to log in.

## Verification Checklist

After setup, verify everything works:

- [ ] Server starts without errors
- [ ] Can access `http://localhost:8000` in browser
- [ ] Login page appears
- [ ] Can log in with `admin` / `admin123`
- [ ] Can log in with `student1` / `password123`
- [ ] Database file exists at `data/app.db`

## Troubleshooting

### "Module not found" errors
- Make sure you've installed dependencies: `pip install -r server/requirements.txt`
- Verify you're using Python 3.8+

### "Database locked" errors
- Make sure no other instance of the server is running
- Close any database viewers (like DBeaver) that might have the database open
- Delete `data/app.db` and restart the server (database will be recreated)

### "No users found" / Can't log in
- **Most common issue:** You forgot to run `python server/database/seed_data.py`
- Run the seed script again: `python server/database/seed_data.py`
- Check that the database file exists: `data/app.db`

### API key errors
- Verify your `.env` file exists in the project root
- Check that `TOGETHER_AI_API_KEY=your_key_here` is in the `.env` file
- Make sure there are no extra spaces or quotes around the key

### Port 8000 already in use
- Stop any other process using port 8000
- Or change the port in `run_server.py` or when running uvicorn directly

## Database Files

The following files are created automatically and should **NOT** be committed to git:
- `data/app.db` - Main database file
- `data/app.db-shm` - SQLite shared memory file
- `data/app.db-wal` - SQLite write-ahead log file

These are already in `.gitignore`.

## Next Steps

Once setup is complete:
1. Log in with one of the test accounts
2. Create a new exam to test question generation
3. Take an exam as a student to test the full workflow
4. Check out `PROJECT_MANUAL.md` for detailed documentation

## Need Help?

If you encounter issues not covered here:
1. Check `PROJECT_MANUAL.md` for detailed documentation
2. Review `DATABASE_SETUP.md` for database-specific issues
3. Contact the team lead (Olivia) for API key or access issues
