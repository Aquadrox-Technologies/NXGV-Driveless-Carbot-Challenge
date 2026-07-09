# 🚀 RISA-bot Git Push, Pull & Deployment Guide

This guide explains the step-by-step workflow for pushing changes from your local PC, pulling changes on both your PC and the robot, and building the workspace. It also covers troubleshooting for common Git errors you might face.

---

## 📥 How to Pull (Get Latest Changes)

You should pull changes in two main scenarios:
1. **On your Local PC**: Before you start writing new code, to make sure you have the latest updates from GitHub.
2. **On the Robot**: After you push changes from your PC, to download the new code onto the robot's hardware.

### Option A: Clean Pull (No Local Modifications)
If you have not edited any files on the machine you are pulling to:

1. **Navigate to the repository directory**:
   - PC: `c:\Users\Lenovo\Downloads\Kerja\RISA-bot-1`
   - Robot: `cd ~/risabotcar_ws/src/RISA-bot`

2. **Verify/Switch your branch**:
   ```bash
   git checkout <branch-name>
   ```
   *Replace `<branch-name>` with the active branch (e.g. `refactor-test`).*

3. **Pull changes**:
   ```bash
   git pull origin <branch-name>
   ```

4. **Rebuild (Robot Only)**:
   ```bash
   cd ~/risabotcar_ws && cb && sos
   ```

---

### Option B: Pulling When You Have Local Edits
If you edited code on the robot or PC, and Git says: *"Your local changes to the following files would be overwritten by merge..."*

#### 1. If you want to DISCARD your local edits and pull:
```bash
# Force-discard local changes
git reset --hard HEAD

# Clean up untracked files/folders
git clean -fd

# Pull the latest code
git pull origin <branch-name>
```

#### 2. If you want to KEEP your local edits and merge them with incoming updates:
```bash
# 1. Temporarily save ("stash") your local edits
git stash

# 2. Pull the latest updates from GitHub
git pull origin <branch-name>

# 3. Bring your local changes back
git stash pop
```
*Note: If there are conflicting changes in the same line of code, Git will ask you to resolve a merge conflict. Open the conflicted file, choose the correct lines, save, and commit.*

---

## 📤 How to Push (Save Local Changes)

Run these commands on your **Local PC** inside the project directory:

1. **Check what changed:**
   ```bash
   git status
   ```

2. **Stage your changes:**
   ```bash
   git add .
   ```

3. **Commit your changes with a message:**
   ```bash
   git commit -m "Describe your changes here"
   ```

4. **Push changes to GitHub:**
   ```bash
   git push origin <branch-name>
   ```

---

## 🌿 Branch Rules for RISA-bot

Always check which branch you are on before pushing or pulling:

| Branch | Purpose | Active Code Features | Launch Command |
|---|---|---|---|
| **`main`** | Development & Testing | Individual node testing | `run_risabot` |
| **`test`** | Competition Mode | Monolithic state machine | `ros2 launch risabot_automode competition.launch.py` |
| **`refactor-test`** | Refactored Competition | Refactored engine + Dashboard | `ros2 launch risabot_automode bringup.launch.py` |

> [!IMPORTANT]
> **Key Rule:** Only perform `git checkout` or `git pull` operations inside the repository directory (`~/risabotcar_ws/src/RISA-bot`). Do not run Git commands from the workspace root (`~/risabotcar_ws`).

---

## 🛠️ Troubleshooting Common Git Errors

### 1. Error: "Updates were rejected because the remote contains work that you do not have locally"
This happens when someone else pushed changes to GitHub, and your local PC is out of sync.

* **Fix (on PC):**
  ```bash
  git pull origin <branch-name>
  # If you get a merge message editor, save and exit.
  # Now push again:
  git push origin <branch-name>
  ```

### 2. Error: "Everything up-to-date" (but changes are not appearing)
This means you committed your changes, but they were either committed on a different branch, or you forgot to push them.

* **Verify active branch and unpushed commits:**
  ```bash
  git branch         # Tells you what branch you are on locally
  git status         # Tells you if you are "ahead of origin" (meaning you need to push)
  ```
* **Fix:**
  ```bash
  git push origin <your-active-branch>
  ```
