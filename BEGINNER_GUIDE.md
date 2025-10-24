# 🎓 SUPER SIMPLE GUIDE (For Beginners)

**If you've never used Python or GitHub before, follow these steps exactly:**

---

## Step 1: Install Python

1. Go to https://www.python.org/downloads/
2. Click the big yellow "Download Python" button
3. Run the installer
4. ✅ **IMPORTANT:** Check the box "Add Python to PATH" during installation
5. Click "Install Now"

---

## Step 2: Download This Project

**Option A - If you have Git:**
```bash
git clone https://github.com/[your-username]/MEGA_neonsportz_stats.git
cd MEGA_neonsportz_stats
```

**Option B - No Git (easier):**
1. Click the green "Code" button on GitHub
2. Click "Download ZIP"
3. Unzip the file to your Desktop
4. Remember where you saved it!

---

## Step 3: Get Your League Data

1. Go to your Neon Sports league
2. Use the **Neon Export** feature to download CSV files
3. You'll get 3 files:
   - `[YourLeagueName]_teams.csv`
   - `[YourLeagueName]_games.csv`
   - `[YourLeagueName]_rankings.csv`
4. **Rename them** to:
   - `MEGA_teams.csv`
   - `MEGA_games.csv`
   - `MEGA_rankings.csv`
5. Put these 3 files in the project folder (same folder as README.md)

---

## Step 4: Run the Script

**On Windows:**
1. Open the project folder
2. Hold `Shift` and right-click in the empty space
3. Click "Open PowerShell window here" or "Open Command Prompt here"
4. Type this command and press Enter:
   ```bash
   python scripts/run_all_playoff_analysis.py
   ```

**On Mac:**
1. Open Terminal (search for "Terminal" in Spotlight)
2. Type `cd ` (with a space after cd)
3. Drag the project folder into Terminal and press Enter
4. Type this command and press Enter:
   ```bash
   python3 scripts/run_all_playoff_analysis.py
   ```

5. Wait for it to finish (you'll see "ALL SCRIPTS COMPLETED SUCCESSFULLY!")

---

## Step 5: Check Your Results

1. Open the `docs` folder in your project
2. Double-click `playoff_race.html`
3. It will open in your web browser
4. 🎉 You did it!

---

# 🌐 Publishing to the Internet (GitHub Pages)

## Step 1: Create GitHub Account (if you don't have one)

1. Go to https://github.com
2. Click "Sign up"
3. Follow the instructions

---

## Step 2: Upload Your Project to GitHub

1. Go to https://github.com/new
2. Name your repository (example: `mega_league`)
3. Click "Create repository"
4. Follow the instructions to upload your files

**Easy way (using GitHub Desktop):**
1. Download GitHub Desktop: https://desktop.github.com
2. Install it and sign in
3. Click "Add" → "Add existing repository"
4. Select your project folder
5. Click "Publish repository"

---

## Step 3: Enable GitHub Pages

1. Go to your repository on GitHub
2. Click "Settings" (top menu)
3. Click "Pages" (left sidebar)
4. Under "Source", select "Deploy from a branch"
5. Under "Branch", select `main` and `/root` (or `/docs`)
6. Click "Save"
7. Wait 1-2 minutes

---

## Step 4: Find Your Website URL

Your website will be at:
```
https://[your-username].github.io/[repository-name]/docs/playoff_race.html
```

Example:
```
https://lespaui.github.io/mega_league/docs/playoff_race.html
```

📖 **Full GitHub Pages Guide:** https://docs.github.com/en/pages

---

# 📰 Embedding in Neon Sports News

Once your page is published on GitHub Pages, you can embed it in Neon Sports:

## Step 1: Create News Article in Neon Sports

1. Go to your Neon Sports league
2. Click "Create News" or "Add Article"
3. Switch to HTML/Code editor mode (<> button)

---

## Step 2: Add Embed Code

Paste this code (replace the URL with YOUR GitHub Pages URL):

```html
<iframe
    src="https://[your-username].github.io/[repository-name]/docs/playoff_race.html"
    title="Mega League Playoff Race"
    style="width: 100%; height: 380vh; border: 0;"
    loading="lazy"
    referrerpolicy="no-referrer"
    sandbox="allow-scripts allow-same-origin allow-popups">
</iframe>
```

**Important:** Change `https://[your-username].github.io/[repository-name]/docs/playoff_race.html` to YOUR URL!

---

## Step 3: Publish the Article

1. Scroll to the bottom of the article editor
2. Change status to **"Publish"**
3. Click "Publish"
4. The article will appear on your league's homepage!

---

## Weekly Updates

Every week:
1. Export new CSV files from Neon Sports
2. Replace the old CSV files in your project folder
3. Run `python3 scripts/run_all_playoff_analysis.py` again
4. Upload the new `docs/playoff_race.html` to GitHub
5. Your embedded page will automatically update!

---

# ❓ Common Questions

**Q: Do I need to pay for GitHub?**  
A: No! GitHub and GitHub Pages are free.

**Q: How do I update my page every week?**  
A: Just run the script again with new CSV files, then push to GitHub.

**Q: Can I customize the colors/design?**  
A: Yes! Edit the HTML files in the `docs` folder.

**Q: What if I get an error?**  
A: Check the Troubleshooting section in README.md, or make sure your CSV files are in the right place.

**Q: Do I need to know programming?**  
A: No! Just follow these steps exactly.

---

# 🎯 Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│  WEEKLY WORKFLOW (After Initial Setup)                  │
├─────────────────────────────────────────────────────────┤
│  1. Export CSV files from Neon Sports                   │
│  2. Replace old CSV files in project folder             │
│  3. Run: python3 scripts/run_all_playoff_analysis.py    │
│  4. Push to GitHub (or upload new files)                │
│  5. Done! Your page updates automatically               │
└─────────────────────────────────────────────────────────┘
```

---

# 📸 Visual Guide

## What Your Folder Should Look Like:

```
MEGA_neonsportz_stats/
├── MEGA_teams.csv          ← Put your CSV files here
├── MEGA_games.csv          ← Put your CSV files here
├── MEGA_rankings.csv       ← Put your CSV files here
├── README.md
├── BEGINNER_GUIDE.md       ← You are here!
├── scripts/
│   └── run_all_playoff_analysis.py
└── docs/
    └── playoff_race.html   ← This is what you'll publish!
```

---

# 🆘 Need Help?

1. **Read the error message carefully** - it usually tells you what's wrong
2. **Check that your CSV files are in the right place** - they should be in the main folder
3. **Make sure Python is installed** - type `python --version` in Terminal/PowerShell
4. **Verify file names are correct** - must be exactly `MEGA_teams.csv`, `MEGA_games.csv`, `MEGA_rankings.csv`
5. **Check the main README.md** - it has a detailed Troubleshooting section

---

**Good luck! 🚀**
