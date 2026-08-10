<#
.SYNOPSIS
    Regenerate repos.json (filtered, star-ranked repo snapshot) for the Pages
    site. Optionally commit it to the Pages repo (default when run locally).
.USAGE
    powershell -ExecutionPolicy Bypass -File tools/update-snapshot.ps1 [-NoDeploy] [-OutFile <path>]
.NOTES
    This is the only copy - refresh-snapshot.yml invokes it with -NoDeploy and
    commits the result itself. Deploying is the default for local runs and goes
    through Commit-Files in gh-commit.ps1.
#>
[CmdletBinding()]
param(
    [switch]$NoDeploy,
    [string]$OutFile
)
$ErrorActionPreference = "Stop"

# Paginate via gh's native flag so we don't silently cap at 100 repos (any
# account that crosses 100 would otherwise produce an incomplete snapshot).
function Invoke-GhJson([string]$Endpoint) {
    $out = gh api --paginate $Endpoint 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "gh api failed (exit $LASTEXITCODE) for $Endpoint`: $($out -join ' ')"
    }
    return $out | ConvertFrom-Json
}

$org = Invoke-GhJson "/orgs/frenzypenguin-media/repos?per_page=100"
$usr = Invoke-GhJson "/users/neohiro/repos?per_page=100&sort=pushed"

$all = @($org) + @($usr) |
    # -not $_.private is a hard requirement, not a tidiness filter. repos.json is
    # published on the Pages site, so any private repo that reaches this pipeline
    # publishes its description, topics and URL to every visitor. The filter used
    # to pass private repos through and stayed harmless only because whoever last
    # ran it had no access to them; run it with an owner-scoped token and the
    # entire private catalogue goes live. See tools/tests/update-snapshot.Tests.ps1.
    Where-Object { -not $_.private -and -not $_.fork -and $_.name -notmatch 'github\.io$' -and $_.name -ne '.github' } |
    # full_name is a total-order tiebreaker on purpose. The org and the user can
    # hold repos with the same name, and Sort-Object is not stable on PS 5.1, so
    # a name tiebreak still leaves the order arbitrary there. full_name is unique
    # across both sources, which makes the ordering total and therefore
    # byte-stable on any runtime.
    #
    # The cross-owner name collision this guards against is no longer present -
    # the org-named repo and its neohiro twin have both been deleted - but the
    # tiebreaker is load-bearing the moment either reappears, so it stays.
    Sort-Object @{e = 'stargazers_count'; Descending = $true }, @{e = 'pushed_at'; Descending = $true }, @{e = 'full_name'; Descending = $false} |
    ForEach-Object {
        # never-pushed repos return $null for pushed_at; preserve null rather than blowing up
        $pushed = if ($_.pushed_at) { ($_.pushed_at -replace 'T.*$', '') } else { $null }
        [ordered]@{
            name             = $_.name
            # Additive: the site ignores unknown keys today, but without an owner
            # two repos sharing a name are indistinguishable in the payload.
            full_name        = $_.full_name
            html_url         = $_.html_url
            description      = $_.description
            stargazers_count = $_.stargazers_count
            forks_count      = $_.forks_count
            language         = $_.language
            topics           = @($_.topics)
            # date-only: GitHub's pushed_at wobbles across edge caches, which would
            # make CI change-detection noisy; the site only displays the date anyway
            pushed_at        = $pushed
        }
    }

# Two owners can hold repos with the same name. index.html keys its repo map by
# lowercased name, so a duplicate name overwrites the earlier entry and that repo
# silently stops resolving. Keep one per name. $all is already sorted by stars
# desc, so the first occurrence is the highest-starred and the choice is
# deterministic; the loser is reported rather than dropped silently.
#
# No cross-owner collision exists at present, so this is a no-op today. It stays
# because the failure it prevents is silent: a merged pair produces a site where
# one of the two repos 404s on click with nothing in CI reporting an error.
$seenNames = @{}
$droppedNames = @()
$deduped = @(
    foreach ($r in $all) {
        if ($seenNames.ContainsKey($r.name)) { $droppedNames += $r.full_name; continue }
        $seenNames[$r.name] = $true
        $r
    }
)
foreach ($d in $droppedNames) {
    Write-Warning "duplicate repo name - omitted from snapshot (keyed by name in index.html): $d"
}
$all = $deduped

$json = ConvertTo-Json @($all) -Depth 4
if ($all.Count -eq 0 -or [string]::IsNullOrWhiteSpace($json)) {
    throw "no repos matched the snapshot filters - refusing to write an empty snapshot"
}
# Repo root, not $PSScriptRoot: repos.json is published from the site root.
    # Walk with Split-Path rather than embedding "..\" - a backslash separator is
    # a literal character in a Linux path, which is where CI runs this.
    if (-not $OutFile) { $OutFile = Join-Path (Split-Path -Parent $PSScriptRoot) "repos.json" }
$outDir = Split-Path -Parent $OutFile
if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
[IO.File]::WriteAllText($OutFile, $json, (New-Object Text.UTF8Encoding($false)))
Write-Host "SNAPSHOT $($all.Count) repos -> $((Resolve-Path -LiteralPath $OutFile).Path)"

if (-not $NoDeploy) {
    # gh-commit.ps1 is the module that actually talks to the API and owns the
    # retry/transaction handling. The previous Deploy-Site call referenced a
    # deploy-site.ps1 that does not exist in this repo, so the local deploy
    # path could never have run.
    . (Join-Path $PSScriptRoot "gh-commit.ps1")
    Commit-Files -Repo "frenzypenguin-media.github.io" -Owner "frenzypenguin-media" `
        -Message "chore: refresh repos.json snapshot" `
        -Changes @(@{ path = "repos.json"; content = $json })
}
