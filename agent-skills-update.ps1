#!/usr/bin/env pwsh

<#
.SYNOPSIS
    Agent Skills Updater v1.0.2
.DESCRIPTION
    Automated skill management for AI coding assistants. Clones skills from multiple
    GitHub repositories, handles different repository structures (standard, root,
    template, multi), and copies files to appropriate directories. Works with Windsurf, Cursor, Claude Code, GitHub Copilot,
    Opencode, Moltbot, and other AI-powered IDEs.
    
    Features:
    - Multi-source updates from any public GitHub repository
    - Structure-aware (standard, root, template, multi-skill layouts)
    - Branch support (clone from specific branches)
    - Lockfile tracking with timestamps
    - External YAML configuration
    - List installed skills (-List)
    - Dry-run mode (-WhatIf)
.PARAMETER Force
    Force overwrite existing skills
.PARAMETER SpecificSkills
    Array of specific skill names to update
.PARAMETER Scheduled
    Mark this run as scheduled (for logging purposes)
.PARAMETER ConfigPath
    Path to agent-skills-config.yaml (default: ./agent-skills-config.yaml)
.PARAMETER List
    Show currently installed skills from lockfile
.PARAMETER WhatIf
    Show what would be updated without making changes (dry run)
.EXAMPLE
    .\agent-skills-update.ps1
    .\agent-skills-update.ps1 -Force
    .\agent-skills-update.ps1 -SpecificSkills copywriting,seo-audit
    .\agent-skills-update.ps1 -List
    .\agent-skills-update.ps1 -WhatIf
#>

param(
    [switch]$Force,
    [string[]]$SpecificSkills,
    [switch]$Scheduled,
    [string]$ConfigPath,
    [switch]$List,
    [switch]$WhatIf
)

# Cross-platform home directory resolution
function Get-HomePath {
    if ($env:HOME) {
        return $env:HOME
    } elseif ($env:USERPROFILE) {
        return $env:USERPROFILE
    } else {
        throw "Cannot determine home directory"
    }
}

# Expand ~ to home directory (cross-platform)
function Expand-TildePath {
    param([string]$Path)
    if ($Path.StartsWith("~")) {
        return $Path.Replace("~", (Get-HomePath))
    }
    return $Path
}

# Default configuration (can be overridden by agent-skills-config.yaml)
$homePath = Get-HomePath
$defaultConfig = @{
    globalSkillsPath = Join-Path $homePath ".agents/skills"
    windsurfSkillsPath = Join-Path $homePath ".codeium/windsurf/skills"
    tempPath = Join-Path $homePath ".temp-agent-skills-update"
    logPath = Join-Path $homePath "scripts/agent-skills-update.log"
}

# Find config file
if (-not $ConfigPath) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ConfigPath = Join-Path $scriptDir "agent-skills-config.yaml"
}

# Load YAML configuration
function Import-YamlConfig {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        Write-Warning "Config file not found: $Path - using built-in defaults"
        return $null
    }
    
    $content = Get-Content $Path -Raw
    $config = @{
        settings = @{}
        repositories = @{}
    }
    
    $currentSection = $null
    $currentRepo = $null
    $inSkillsList = $false
    $skills = [System.Collections.ArrayList]@()
    
    # Helper to save current skills to repo
    function Save-CurrentSkills {
        if ($currentRepo -and $skills.Count -gt 0) {
            $config.repositories[$currentRepo]['skills'] = @($skills)
        }
    }
    
    foreach ($line in $content -split "`n") {
        $line = $line.TrimEnd("`r", "`n", " ", "`t")
        
        # Skip comments and empty lines
        if ($line -match '^\s*#' -or $line -match '^\s*$') { continue }
        
        # Count leading spaces
        $trimmed = $line.TrimStart()
        $indent = $line.Length - $trimmed.Length
        
        # Top-level sections (0 indent)
        if ($indent -eq 0) {
            if ($line -eq 'settings:') {
                Save-CurrentSkills
                $currentSection = 'settings'
                $currentRepo = $null
                $inSkillsList = $false
                continue
            }
            if ($line -eq 'repositories:') {
                Save-CurrentSkills
                $currentSection = 'repositories'
                $currentRepo = $null
                $inSkillsList = $false
                continue
            }
        }
        
        # Settings (2 spaces)
        if ($currentSection -eq 'settings' -and $indent -eq 2) {
            if ($trimmed -match '^(\w+):\s*(.+)$') {
                $config.settings[$Matches[1]] = Expand-TildePath $Matches[2].Trim()
            }
            continue
        }
        
        # Repository name (2 spaces, ends with :, no value)
        if ($currentSection -eq 'repositories' -and $indent -eq 2) {
            if ($trimmed -match '^([^:]+):\s*$') {
                Save-CurrentSkills
                $currentRepo = $Matches[1].Trim()
                $config.repositories[$currentRepo] = @{}
                $skills = [System.Collections.ArrayList]@()
                $inSkillsList = $false
            }
            continue
        }
        
        # Repository properties (4 spaces)
        if ($currentSection -eq 'repositories' -and $currentRepo -and $indent -eq 4) {
            if ($trimmed -match '^(\w+):\s*(.*)$') {
                $key = $Matches[1]
                $value = $Matches[2].Trim()
                
                if ($key -eq 'skills' -and $value -eq '') {
                    # Save any previous skills first, then start new list
                    $skills = [System.Collections.ArrayList]@()
                    $inSkillsList = $true
                } else {
                    $inSkillsList = $false
                    $config.repositories[$currentRepo][$key] = $value
                }
            }
            continue
        }
        
        # Skills list items (6 spaces + dash)
        if ($inSkillsList -and $indent -eq 6 -and $trimmed.StartsWith('-')) {
            $skillName = $trimmed.Substring(1).Trim()
            [void]$skills.Add($skillName)
            continue
        }
    }
    
    # Save last repo's skills
    Save-CurrentSkills
    
    return $config
}

# Load configuration
$yamlConfig = Import-YamlConfig -Path $ConfigPath

# Apply settings (YAML overrides defaults)
$globalSkillsPath = if ($yamlConfig -and $yamlConfig.settings.globalSkillsPath) { 
    $yamlConfig.settings.globalSkillsPath 
} else { 
    $defaultConfig.globalSkillsPath 
}
$windsurfSkillsPath = if ($yamlConfig -and $yamlConfig.settings.windsurfSkillsPath) { 
    $yamlConfig.settings.windsurfSkillsPath 
} else { 
    $defaultConfig.windsurfSkillsPath 
}
$tempPath = if ($yamlConfig -and $yamlConfig.settings.tempPath) { 
    $yamlConfig.settings.tempPath 
} else { 
    $defaultConfig.tempPath 
}
$logPath = if ($yamlConfig -and $yamlConfig.settings.logPath) { 
    $yamlConfig.settings.logPath 
} else { 
    $defaultConfig.logPath 
}

# Build skill repos from config or use defaults
$skillRepos = @{}

if ($yamlConfig -and $yamlConfig.repositories.Count -gt 0) {
    foreach ($repoName in $yamlConfig.repositories.Keys) {
        $repo = $yamlConfig.repositories[$repoName]
        $skillRepos[$repoName] = @{
            Url = $repo.url
            Skills = $repo.skills
        }
        if ($repo.branch) {
            $skillRepos[$repoName].Branch = $repo.branch
        }
        if ($repo.structure) {
            $skillRepos[$repoName].SpecialStructure = $repo.structure
        }
    }
} else {
    # Built-in defaults if no config file
    $skillRepos = @{
        "coreyhaines31/marketingskills" = @{
            Url = "https://github.com/coreyhaines31/marketingskills.git"
            Skills = @(
                "ab-test-setup", "analytics-tracking", "competitor-alternatives", "copy-editing", 
                "copywriting", "email-sequence", "form-cro", "free-tool-strategy", "launch-strategy",
                "marketing-ideas", "marketing-psychology", "onboarding-cro", "page-cro", "paid-ads",
                "paywall-upgrade-cro", "popup-cro", "pricing-strategy", "programmatic-seo",
                "referral-program", "schema-markup", "seo-audit", "signup-flow-cro", "social-content"
            )
        }
        "vercel-labs/agent-skills" = @{
            Url = "https://github.com/vercel-labs/agent-skills.git"
            Skills = @("web-design-guidelines")
        }
        "anthropics/skills" = @{
            Url = "https://github.com/anthropics/skills.git"
            Skills = @("frontend-design")
        }
        "vercel-labs/skills" = @{
            Url = "https://github.com/vercel-labs/skills.git"
            Skills = @("find-skills")
        }
        "resend/email-best-practices" = @{
            Url = "https://github.com/resend/email-best-practices.git"
            Skills = @("email-best-practices")
            SpecialStructure = "root"
        }
        "resend/react-email" = @{
            Url = "https://github.com/resend/react-email.git"
            Skills = @("react-email")
            Branch = "canary"
        }
        "resend/resend-skills" = @{
            Url = "https://github.com/resend/resend-skills.git"
            Skills = @("resend")
            SpecialStructure = "multi"
        }
    }
}

# Logging function
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Write to console with colors
    switch ($Level) {
        "INFO" { Write-Host $Message -ForegroundColor White }
        "SUCCESS" { Write-Host $Message -ForegroundColor Green }
        "WARNING" { Write-Host $Message -ForegroundColor Yellow }
        "ERROR" { Write-Host $Message -ForegroundColor Red }
        "CYAN" { Write-Host $Message -ForegroundColor Cyan }
        "BLUE" { Write-Host $Message -ForegroundColor Blue }
    }
    
    # Write to log file
    $logDir = Split-Path -Parent $logPath
    if ($logDir -and -not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    Add-Content -Path $logPath -Value $logEntry
}

# Initialize log file
if (-not (Test-Path $logPath)) {
    $logDir = Split-Path -Parent $logPath
    if ($logDir -and -not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    "# Agent Skills Update Log - Created $(Get-Date)" | Out-File -FilePath $logPath
}

if ($Scheduled) {
    Write-Log "=== SCHEDULED SKILLS UPDATE STARTED ===" "INFO"
} else {
    Write-Log "=== MANUAL SKILLS UPDATE STARTED ===" "INFO"
}

# Add diagnostic info
Write-Log "PowerShell Version: $($PSVersionTable.PSVersion)" "INFO"
Write-Log "Platform: $($PSVersionTable.Platform)" "INFO"
Write-Log "Config: $ConfigPath" "INFO"
Write-Log "Skills Path: $globalSkillsPath" "INFO"

function Update-SkillFromRepo {
    param(
        [string]$RepoName,
        [string]$RepoUrl,
        [string[]]$Skills,
        [string]$TempDir,
        [string]$SpecialStructure = $null,
        [string]$Branch = $null
    )
    
    Write-Log "Processing $RepoName..." "INFO"
    
    # Clone repository
    Write-Log "   Cloning repository..." "INFO"
    $repoTempDir = Join-Path $TempDir ($RepoName.Replace("/", "_"))
    
    if (Test-Path $repoTempDir) {
        Remove-Item $repoTempDir -Recurse -Force
    }
    
    if ($Branch) {
        git clone --branch $Branch --single-branch $RepoUrl $repoTempDir --quiet 2>&1 | Out-Null
    } else {
        git clone $RepoUrl $repoTempDir --quiet 2>&1 | Out-Null
    }
    
    if (-not (Test-Path $repoTempDir)) {
        Write-Log "   ERROR: Failed to clone $RepoName" "ERROR"
        return $null
    }
    
    # Find skills directory
    $skillsSourceDir = $null
    
    if ($SpecialStructure -eq "root") {
        $skillsSourceDir = $repoTempDir
        Write-Log "   Using root directory structure (SKILL.md in root)" "INFO"
    } elseif ($SpecialStructure -eq "template") {
        $skillsSourceDir = Join-Path $repoTempDir "template"
        Write-Log "   Using template directory structure (SKILL.md in template/)" "INFO"
    } elseif ($SpecialStructure -eq "multi") {
        $skillsSourceDir = $repoTempDir
        Write-Log "   Using multi-skill structure (subdirectories)" "INFO"
    } else {
        # Standard structure - look for skills/ subdirectory
        $possiblePaths = @(
            (Join-Path $repoTempDir "skills"),
            (Join-Path $repoTempDir ""),
            (Join-Path (Join-Path $repoTempDir "src") "skills")
        )
        
        foreach ($path in $possiblePaths) {
            if (Test-Path $path) {
                if ($SpecialStructure -eq "root") {
                    $testSkill = Join-Path $path "SKILL.md"
                } else {
                    $testSkill = Join-Path (Join-Path $path $Skills[0]) "SKILL.md"
                }
                if (Test-Path $testSkill) {
                    $skillsSourceDir = $path
                    break
                }
            }
        }
    }
    
    if (-not $skillsSourceDir) {
        Write-Log "   ERROR: Could not find skills directory in $RepoName" "ERROR"
        return $null
    }
    
    # Copy skills to both locations
    $updatedSkills = @()
    $skillPaths = @{}
    
    foreach ($skillName in $Skills) {
        if ($SpecificSkills -and $skillName -notin $SpecificSkills) {
            continue
        }
        
        # Determine skill source based on structure type
        if ($SpecialStructure -eq "root") {
            $skillSource = $skillsSourceDir
            $destName = $skillName
            if (-not (Test-Path (Join-Path $skillSource "SKILL.md"))) {
                Write-Log "   WARNING: SKILL.md not found in root directory" "WARNING"
                continue
            }
        } elseif ($SpecialStructure -eq "template") {
            $skillSource = $skillsSourceDir
            $destName = $skillName
            if (-not (Test-Path (Join-Path $skillSource "SKILL.md"))) {
                Write-Log "   WARNING: SKILL.md not found in template directory" "WARNING"
                continue
            }
        } elseif ($SpecialStructure -eq "multi") {
            # For multi-skill repos, find all subdirectories with SKILL.md
            $subSkills = Get-ChildItem $skillsSourceDir -Directory | Where-Object { 
                Test-Path (Join-Path $_.FullName "SKILL.md") 
            }
            foreach ($subSkill in $subSkills) {
                $destName = $subSkill.Name
                $globalDest = Join-Path $globalSkillsPath $destName
                $windsurfDest = Join-Path $windsurfSkillsPath $destName
                
                if (Test-Path $globalDest) {
                    if ($Force) {
                        Remove-Item $globalDest -Recurse -Force
                    } else {
                        continue
                    }
                }
                Copy-Item $subSkill.FullName $globalDest -Recurse -Force
                Write-Log "   Copied $destName to global directory" "INFO"
                
                if (Test-Path $windsurfDest) {
                    Remove-Item $windsurfDest -Recurse -Force
                }
                Copy-Item $subSkill.FullName $windsurfDest -Recurse -Force
                Write-Log "   Copied $destName to Windsurf directory" "INFO"
                
                $updatedSkills += $destName
            }
            continue
        } else {
            # Standard structure
            $skillSource = $null
            $directPath = Join-Path (Join-Path $skillsSourceDir $skillName) "SKILL.md"
            if (Test-Path $directPath) {
                $skillSource = Join-Path $skillsSourceDir $skillName
            } else {
                # Recursive search - renamed from $matches to $skillMatches to avoid automatic variable conflict
                $skillMatches = Get-ChildItem -Path $skillsSourceDir -Recurse -Filter "SKILL.md" -ErrorAction SilentlyContinue | Where-Object {
                    $_.FullName -match ([regex]::Escape([System.IO.Path]::DirectorySeparatorChar + $skillName + [System.IO.Path]::DirectorySeparatorChar) + "SKILL\.md$")
                } | Select-Object -First 1
                if ($skillMatches) {
                    $skillSource = Split-Path -Parent $skillMatches.FullName
                }
            }
            $destName = $skillName
        }
        
        if (-not $skillSource -or -not (Test-Path $skillSource)) {
            Write-Log "   WARNING: Skill $skillName not found in $RepoName" "WARNING"
            continue
        }
        
        $skillMdPath = Join-Path $skillSource "SKILL.md"
        if (Test-Path $skillMdPath) {
            $relativeSkillPath = $skillMdPath.Substring($repoTempDir.Length + 1).Replace('\', '/')
            $skillPaths[$destName] = $relativeSkillPath
        }
        
        # Copy to global .agents directory
        $globalDest = Join-Path $globalSkillsPath $destName
        if (Test-Path $globalDest) {
            if ($Force) {
                Remove-Item $globalDest -Recurse -Force
            } else {
                Write-Log ('   Skipping ' + $destName + ' (already exists, use -Force)') 'WARNING'
                continue
            }
        }
        
        if (-not $WhatIf) {
            Copy-Item $skillSource $globalDest -Recurse -Force
            Write-Log "   Copied $destName to global directory" "SUCCESS"
        } else {
            Write-Log "   Would copy $destName to global directory" "INFO"
        }
        
        # Copy to Windsurf directory
        $windsurfDest = Join-Path $windsurfSkillsPath $destName
        if (Test-Path $windsurfDest) {
            Remove-Item $windsurfDest -Recurse -Force
        }
        if (-not $WhatIf) {
            Copy-Item $skillSource $windsurfDest -Recurse -Force
            Write-Log "   Copied $destName to Windsurf directory" "SUCCESS"
        } else {
            Write-Log "   Would copy $destName to Windsurf directory" "INFO"
        }
        
        $updatedSkills += $destName
    }
    
    Write-Log "   Updated $($updatedSkills.Count) skills from $RepoName" "INFO"
    return @{
        RepoName = $RepoName
        RepoUrl = $RepoUrl
        Skills = $updatedSkills
        SkillPaths = $skillPaths
    }
}

function Update-SkillLockfile {
    param([hashtable]$UpdatedSkills)
    
    $lockfile = Join-Path (Split-Path -Parent $globalSkillsPath) ".skill-lock.json"
    
    if (-not (Test-Path $lockfile)) {
        # Create new lockfile
        $lockData = [pscustomobject]@{
            version = "1.0"
            skills = [pscustomobject]@{}
        }
    } else {
        $lockData = Get-Content $lockfile | ConvertFrom-Json
    }
    
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
    
    foreach ($repo in $UpdatedSkills.Keys) {
        $repoUpdate = $UpdatedSkills[$repo]
        $skillsList = @()
        $skillPaths = @{}
        $sourceRepo = $repo
        $sourceUrl = $null
        
        if ($repoUpdate -is [hashtable] -and $repoUpdate.ContainsKey('Skills')) {
            $skillsList = $repoUpdate.Skills
            if ($repoUpdate.ContainsKey('SkillPaths')) {
                $skillPaths = $repoUpdate.SkillPaths
            }
            if ($repoUpdate.ContainsKey('RepoName')) {
                $sourceRepo = $repoUpdate.RepoName
            }
            if ($repoUpdate.ContainsKey('RepoUrl')) {
                $sourceUrl = $repoUpdate.RepoUrl
            }
        } else {
            $skillsList = $repoUpdate
        }
        
        foreach ($skill in $skillsList) {
            if (-not ($lockData.skills.PSObject.Properties.Name -contains $skill)) {
                $lockData.skills | Add-Member -MemberType NoteProperty -Name $skill -Value ([pscustomobject]@{
                    source = $sourceRepo
                    sourceType = 'github'
                    sourceUrl = ''
                    skillPath = ''
                    skillFolderHash = ''
                    installedAt = $timestamp
                    updatedAt = $timestamp
                })
            }
            
            if ($sourceUrl) {
                $lockData.skills."$skill".sourceUrl = $sourceUrl
            }
            $lockData.skills."$skill".source = $sourceRepo
            $lockData.skills."$skill".updatedAt = $timestamp
            if ($skillPaths.ContainsKey($skill)) {
                $lockData.skills."$skill".skillPath = $skillPaths[$skill]
            }
            Write-Log "   Updated timestamp for $skill" "INFO"
        }
    }
    
    $lockData | ConvertTo-Json -Depth 10 | Set-Content $lockfile
    Write-Log "Updated skill-lock.json" "SUCCESS"
}

# List installed skills if requested
if ($List) {
    $lockfile = Join-Path (Split-Path -Parent $globalSkillsPath) ".skill-lock.json"
    if (Test-Path $lockfile) {
        $lockData = Get-Content $lockfile | ConvertFrom-Json
        Write-Host "Installed skills:" -ForegroundColor Cyan
        $lockData.skills.PSObject.Properties | ForEach-Object {
            $skill = $_
            Write-Host "  - $($skill.Name)" -ForegroundColor White
            Write-Host "    Source: $($skill.Value.source)" -ForegroundColor Gray
            Write-Host "    Updated: $($skill.Value.updatedAt)" -ForegroundColor Gray
            if ($skill.Value.skillPath) {
                Write-Host "    Path: $($skill.Value.skillPath)" -ForegroundColor Gray
            }
            Write-Host ""
        }
    } else {
        Write-Host "No lockfile found. No skills installed yet." -ForegroundColor Yellow
    }
    return
}

# Main execution
Write-Log "Starting Agent Skills Update..." "INFO"
Write-Log "" "INFO"

# Create temp directory
if (Test-Path $tempPath) {
    Remove-Item $tempPath -Recurse -Force
}
New-Item -ItemType Directory -Path $tempPath -Force | Out-Null

# Ensure target directories exist
if (-not (Test-Path $globalSkillsPath)) {
    New-Item -ItemType Directory -Path $globalSkillsPath -Force | Out-Null
}
if (-not (Test-Path $windsurfSkillsPath)) {
    New-Item -ItemType Directory -Path $windsurfSkillsPath -Force | Out-Null
}

$allUpdatedSkills = @{}

try {
    foreach ($repo in $skillRepos.Keys) {
        $repoInfo = $skillRepos[$repo]
        $specialStruct = $repoInfo.SpecialStructure
        $branch = $repoInfo.Branch
        $result = Update-SkillFromRepo -RepoName $repo -RepoUrl $repoInfo.Url -Skills $repoInfo.Skills -TempDir $tempPath -SpecialStructure $specialStruct -Branch $branch
        if ($result -and $result.Skills -and $result.Skills.Count -gt 0) {
            $allUpdatedSkills[$repo] = $result
        }
        Write-Log "" "INFO"
    }

    # Update lockfile (skip in WhatIf mode)
    if ($allUpdatedSkills.Count -gt 0 -and -not $WhatIf) {
        Update-SkillLockfile -UpdatedSkills $allUpdatedSkills
    }

    Write-Log "Skills update completed!" "SUCCESS"
    Write-Log "" "INFO"
    Write-Log "Summary:" "INFO"
    foreach ($repo in $allUpdatedSkills.Keys) {
        $count = 0
        if ($allUpdatedSkills[$repo] -is [hashtable] -and $allUpdatedSkills[$repo].ContainsKey('Skills')) {
            $count = $allUpdatedSkills[$repo].Skills.Count
        } else {
            $count = $allUpdatedSkills[$repo].Count
        }
        Write-Log "   ${repo}: $count skills updated" "INFO"
    }
}
finally {
    # Cleanup
    if (Test-Path $tempPath) {
        Remove-Item $tempPath -Recurse -Force
        Write-Log "Cleaned up temporary files" "INFO"
    }
}

Write-Log "" "INFO"
if ($WhatIf) {
    Write-Log "DRY RUN COMPLETE - No files were modified" "INFO"
    Write-Log "" "INFO"
} else {
    Write-Log "Done! Your skills are now up to date." "SUCCESS"
}
Write-Log "" "INFO"
Write-Log "Usage examples:" "INFO"
Write-Log "   .\agent-skills-update.ps1                    # Update all skills" "INFO"
Write-Log "   .\agent-skills-update.ps1 -Force             # Force overwrite existing" "INFO"
Write-Log "   .\agent-skills-update.ps1 -SpecificSkills copywriting,seo-audit  # Specific skills" "INFO"
Write-Log "   .\agent-skills-update.ps1 -List              # Show installed skills" "INFO"
Write-Log "   .\agent-skills-update.ps1 -WhatIf            # Dry run (show what would be updated)" "INFO"
