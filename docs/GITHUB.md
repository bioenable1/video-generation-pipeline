# Push to GitHub

Run once after [installing GitHub CLI](https://cli.github.com/) and logging in.

## One-time: authenticate

```powershell
gh auth login
# Choose: GitHub.com → HTTPS → Login with browser
```

## Create repo and push

```powershell
cd C:\development\Video-Generation

# Create public repo under your account and push
gh repo create video-generation-pipeline --public --source=. --remote=origin --description "Agent-driven product marketing video pipeline for Cursor — free FFmpeg render + optional VEED/ElevenLabs" --push
```

If the repo name is taken, pick another:

```powershell
gh repo create bioenable-video-generation --public --source=. --remote=origin --push
```

## Already have a remote?

```powershell
git remote add origin https://github.com/YOUR_USERNAME/video-generation-pipeline.git
git branch -M main
git push -u origin main
```

## Large files

Sample video and stock clips are ~200 MB total. If push fails on a single file >100 MB, run:

```powershell
git lfs install
git lfs track "*.mp4"
git add .gitattributes
git add projects/iriuniverse2-launch/renders/final.mp4 projects/iriuniverse2-launch/assets/stock/*.mp4
git commit -m "Track large video assets with Git LFS"
git push
```
