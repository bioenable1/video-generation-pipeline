#Requires -Version 5.1
<#
.SYNOPSIS
  Create GitHub repo and push Video Generation Pipeline.

.USAGE
  1. gh auth login
  2. .\scripts\push-to-github.ps1
  3. Optional: .\scripts\push-to-github.ps1 -RepoName "my-custom-name" -Private
#>
param(
    [string]$RepoName = "video-generation-pipeline",
    [switch]$Private
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

$visibility = if ($Private) { "--private" } else { "--public" }

Write-Host "Checking gh auth..."
gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run: gh auth login"
    exit 1
}

if (git remote get-url origin 2>$null) {
    Write-Host "Remote origin exists. Pushing..."
    git push -u origin main
    exit $LASTEXITCODE
}

Write-Host "Creating repo: $RepoName ($visibility)"
gh repo create $RepoName $visibility --source=. --remote=origin `
    --description "Agent-driven product marketing video pipeline for Cursor (free FFmpeg + optional VEED/ElevenLabs)" `
    --push

if ($LASTEXITCODE -eq 0) {
    $url = gh repo view --json url -q .url
    Write-Host "`nDone: $url"
}
