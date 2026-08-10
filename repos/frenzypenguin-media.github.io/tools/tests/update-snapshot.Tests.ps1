<#
.SYNOPSIS
    Tests for tools/update-snapshot.ps1 - the repos.json generator.

.DESCRIPTION
    The snapshot is a public artifact: it is committed to the Pages repo and
    served to every visitor of frenzypenguin.media. Its one hard requirement is
    that no private repo ever appears in it.

    The privacy bug this guards against is subtle. `gh api /orgs/X/repos` returns
    private repos when the caller has sufficient access, so the generator's
    output depends on the token that ran it. That made a leak possible and
    invisible at the same time: a maintainer without access produces a correct
    file, and nobody notices the filter is missing until someone with owner
    access commits a snapshot full of private repo descriptions.

    These tests drive the real filter expression extracted from the shipped
    script, not a copy of it, so they fail if the filter is weakened again.

    Written for Pester 3.4: there is no file-level BeforeAll in that version, so
    shared setup lives at the top of each Describe block.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -Command `
      "Import-Module Pester; Invoke-Pester '.\tools\tests\update-snapshot.Tests.ps1'"
#>

Describe 'snapshot privacy filter' {

    # ── shared setup (Pester 3.4 has no file-level BeforeAll) ───────────────
    $scriptPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'update-snapshot.ps1'
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        throw "update-snapshot.ps1 not found at $scriptPath"
    }
    $source = [IO.File]::ReadAllText($scriptPath)

    $m = [regex]::Match($source, '(?ms)^\s*Where-Object\s*\{(?<body>[^}]*)\}\s*\|\s*$')
    if (-not $m.Success) {
        throw "could not locate the snapshot Where-Object filter in $scriptPath"
    }
    $filterBody = $m.Groups['body'].Value

    function Test-SnapshotFilter {
        param([object[]]$Repo)
        return @($Repo | Where-Object { Invoke-Expression $filterBody })
    }

    function New-Repo {
        param(
            [string]$Name,
            [string]$FullName,
            [bool]$Private = $false,
            [bool]$Fork = $false,
            [string]$Description = ''
        )
        return [pscustomobject]@{
            name              = $Name
            full_name         = $FullName
            private           = $Private
            fork              = $Fork
            html_url          = "https://github.com/$FullName"
            description       = $Description
            stargazers_count  = 0
            forks_count       = 0
            language          = $null
            topics            = @()
            pushed_at         = '2026-10-05T00:00:00Z'
        }
    }

    # ── tests ───────────────────────────────────────────────────────────────

    It 'excludes a private repo' {
        $private = New-Repo -Name 'BIBI' -FullName 'frenzypenguin-media/BIBI' -Private $true
        $result = @(Test-SnapshotFilter -Repo @($private))
        @($result).Count | Should Be 0
    }

    It 'keeps a public repo of the same shape' {
        $public = New-Repo -Name 'github-social' -FullName 'frenzypenguin-media/github-social'
        $result = @(Test-SnapshotFilter -Repo @($public))
        $result.Count | Should Be 1
        $result[0].full_name | Should Be 'frenzypenguin-media/github-social'
    }

    It 'excludes a mixed batch of private and public repos, keeping only the public ones' {
        # This is the real-world shape: one API call returns both.
        $batch = @(
            New-Repo -Name 'BIBI'         -FullName 'frenzypenguin-media/BIBI'         -Private $true
            New-Repo -Name 'github-social' -FullName 'frenzypenguin-media/github-social'
            New-Repo -Name 'doctor'        -FullName 'frenzypenguin-media/doctor'        -Private $true
            New-Repo -Name 'monetization'  -FullName 'frenzypenguin-media/monetization'  -Private $true
            New-Repo -Name 'marketing'     -FullName 'frenzypenguin-media/marketing'     -Private $true
            New-Repo -Name 'tristar-mania' -FullName 'frenzypenguin-media/tristar-mania'
        )
        $kept = @(@(Test-SnapshotFilter -Repo $batch) | ForEach-Object { $_.full_name })
        ($kept -contains 'frenzypenguin-media/BIBI') | Should Be $false
        ($kept -contains 'frenzypenguin-media/doctor') | Should Be $false
        ($kept -contains 'frenzypenguin-media/monetization') | Should Be $false
        ($kept -contains 'frenzypenguin-media/marketing') | Should Be $false
        $kept.Count | Should Be 2
    }

    It 'excludes forks, github.io sites and the .github community repo' {
        $batch = @(
            New-Repo -Name 'some-fork'                        -FullName 'frenzypenguin-media/some-fork'  -Fork $true
            New-Repo -Name 'frenzypenguin-media.github.io'   -FullName 'frenzypenguin-media/frenzypenguin-media.github.io'
            New-Repo -Name '.github'                         -FullName 'frenzypenguin-media/.github'
            New-Repo -Name 'keeps-working'                   -FullName 'frenzypenguin-media/keeps-working'
        )
        $kept = @(@(Test-SnapshotFilter -Repo $batch) | ForEach-Object { $_.full_name })
        $kept.Count | Should Be 1
        $kept[0] | Should Be 'frenzypenguin-media/keeps-working'
    }

    It 'filters on the private flag rather than on name or description' {
        # A private repo whose name and description look entirely public must
        # still be excluded, otherwise the guard degrades into a naming
        # convention that someone will eventually break.
        $sneaky = New-Repo -Name 'public-looking' -FullName 'frenzypenguin-media/public-looking' `
            -Private $true -Description 'A perfectly ordinary public repository'
        $result = @(Test-SnapshotFilter -Repo @($sneaky))
        @($result).Count | Should Be 0
    }
}

Describe 'committed snapshot is safe to publish' {

    # ── shared setup ────────────────────────────────────────────────────────
    $repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $snapshotPath = Join-Path $repoRoot 'repos.json'

    It 'contains no entry that names a private repo' {
        # Guards the artifact, not just the generator: a snapshot committed
        # before the privacy filter existed must not stay live.
        if (-not (Test-Path -LiteralPath $snapshotPath)) { return }

        $rows = ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($snapshotPath))
        $rows.Count | Should BeGreaterThan 0

        $leaked = New-Object System.Collections.Generic.List[string]
        foreach ($row in $rows) {
            if (-not $row.full_name) {
                $leaked.Add("<entry '$($row.name)' has no full_name>")
                continue
            }
            $probe = gh api "repos/$($row.full_name)" --jq '.private' 2>$null
            if ($LASTEXITCODE -eq 0 -and ($probe -join '').Trim() -eq 'true') {
                $leaked.Add($row.full_name)
            }
        }

        @($leaked).Count | Should Be 0
    }

    It 'contains no entry that 404s, which would render as a dead card on the site' {
        # index.html keys its repo map by name, so a stale entry silently
        # breaks that card rather than failing loudly.
        if (-not (Test-Path -LiteralPath $snapshotPath)) { return }

        $rows = ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($snapshotPath))
        $dead = New-Object System.Collections.Generic.List[string]
        foreach ($row in $rows) {
            gh api "repos/$($row.full_name)" --jq '.full_name' 2>$null | Out-Null
            if ($LASTEXITCODE -ne 0) { $dead.Add($row.full_name) }
        }

        @($dead).Count | Should Be 0
    }
}
