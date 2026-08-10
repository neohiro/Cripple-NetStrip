function Commit-Files {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$Repo,
        [Parameter(Mandatory)][string]$Message,
        [Parameter(Mandatory)][array]$Changes,
        [string]$Branch = "main",
        [string]$Owner = "neohiro",
        [int]$Retries = 3,
        [switch]$NoOcTag,
        [switch]$NoAgentIdentity
    )
    # $env:TEMP only exists on Windows. On the Linux runner it is unset, and
    # Join-Path $null threw "Cannot bind argument to parameter 'Path'", which
    # failed refresh-snapshot.yml on every scheduled run. Fall back through
    # TMPDIR (what GitHub Actions sets) and then the runtime's own answer.
    $tmpRoot = if ($env:TEMP) { $env:TEMP } elseif ($env:TMPDIR) { $env:TMPDIR } else { [IO.Path]::GetTempPath() }
    $tmpDir = Join-Path $tmpRoot "opencode"
    if (-not (Test-Path -LiteralPath $tmpDir)) { New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null }
    $tmp = Join-Path $tmpDir ("ghapi-$PID-" + [guid]::NewGuid().ToString("N") + ".json")

    function Cleanup {
        if ($tmp -and (Test-Path -LiteralPath $tmp)) {
            Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        }
    }
    try {

    # Transient = worth retrying. Everything else fails fast.
    function Test-Transient([string]$err) {
        $err -match 'HTTP 5\d\d' -or
        $err -match 'rate limit' -or
        $err -match 'timed? ?out|connection|Could not resolve|SSL|EOF|empty stream'
    }

    function Invoke-GhApi {
        param([string[]]$GhArgs)
        for ($i = 0; ; $i++) {
            # EAP=Continue locally so merged stderr (2>&1) never becomes terminating under caller's -ErrorActionPreference Stop
            $prevEap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
            try { $out = & gh api @GhArgs 2>&1 } finally { $ErrorActionPreference = $prevEap }
            if ($LASTEXITCODE -eq 0) { return (($out | Out-String).Trim()) }
            $err = ($out | Out-String)
            if ($i -ge $Retries -or -not (Test-Transient $err)) {
                throw "gh api failed ($($GhArgs -join ' ')): $($err.Trim())"
            }
            $delay = [Math]::Pow(2, $i) * 2 + (Get-Random -Maximum 1.5)
            Write-Warning "transient failure, retry $($i+1)/$Retries in $([int]$delay)s"
            Start-Sleep -Seconds $delay
        }
    }

    function ApiIn([string]$method, [string]$endpoint, [string]$json) {
        # BOM-less UTF-8: preserves non-ASCII messages (Ascii corrupts them, UTF8-PS adds a BOM GitHub may reject)
        [IO.File]::WriteAllText($tmp, $json, (New-Object Text.UTF8Encoding($false)))
        Invoke-GhApi @("-X", $method, "/repos/$Owner/$Repo/$endpoint", "--input", $tmp)
    }

    # Dry-run gate: pure-local plan summary, zero network mutations on -WhatIf / -Confirm
    if (-not $NoOcTag -and $Message -notmatch '\[oc\]') {
        # Agent-session marker: CI runs soft (no failure email) for these pushes
        $Message = "$Message [oc]"
    }
    $plan = foreach ($c in $Changes) {
        if ($c.delete) { "[delete] $($c.path)" }
        elseif ($c.ContainsKey("bytes")) { "[write] $($c.path) ($($c.bytes.Length) bytes)" }
        else { "[write] $($c.path) ($($c.content.Length) chars)" }
    }
    if (-not $PSCmdlet.ShouldProcess("$Owner/$Repo",
        "commit $($Changes.Count) file(s) to branch '$Branch':`n$($plan -join "`n")")) { return }

    # 1. current branch head
    $ref = Invoke-GhApi @("/repos/$Owner/$Repo/git/ref/heads/$Branch") | ConvertFrom-Json
    $commitSha = $ref.object.sha
    # Defensive: if the ref points to a tag (type "tag") rather than a commit, follow it.
    # This cannot happen with a normal main branch on GitHub Pages but guards against
    # a non-standard setup or a tag being mistakenly used as the default branch.
    if ($ref.object.type -eq 'tag') {
        $tagObj = Invoke-GhApi @("/repos/$Owner/$Repo/git/tags/$commitSha") | ConvertFrom-Json
        $commitSha = $tagObj.object.sha
    }
    $commitObj = Invoke-GhApi @("/repos/$Owner/$Repo/git/commits/$commitSha") | ConvertFrom-Json
    $baseTree = $commitObj.tree.sha

    # 2. blobs + tree entries
    $entries = @()
    foreach ($c in $Changes) {
        if ($c.delete) {
            $entries += @{ path = $c.path; mode = "100644"; type = "blob"; sha = $null }
            continue
        }
        if ($c.ContainsKey("bytes")) {
            $b64 = [Convert]::ToBase64String($c.bytes)
        } else {
            $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($c.content))
        }
        $resp = ApiIn "POST" "git/blobs" (@{ content = $b64; encoding = "base64" } | ConvertTo-Json)
        $blobSha = ($resp | ConvertFrom-Json).sha
        if (-not $blobSha) { throw "Blob creation failed for $($c.path): $resp" }
        $entries += @{ path = $c.path; mode = "100644"; type = "blob"; sha = $blobSha }
    }
    if (-not $entries) { throw "No changes supplied for ${Owner}/${Repo}" }

    $treeResp = ApiIn "POST" "git/trees" (@{ base_tree = $baseTree; tree = $entries } | ConvertTo-Json -Depth 2)
    $newTree = ($treeResp | ConvertFrom-Json).sha
    if (-not $newTree) { throw "Tree creation failed for ${Repo}: $treeResp" }

    # 3. commit + update ref
    $body = @{ message = $Message; tree = $newTree; parents = @($commitSha) }
    if (-not $NoAgentIdentity) {
        # Git-level agent marker: survives any push transport, lets CI triage
        # distinguish agent commits from human ones without relying on tags.
        $agent = @{ name = "OpenCode Agent"; email = "opencode-agent@users.noreply.github.com" }
        $body.author = $agent
        $body.committer = $agent
    }
    $commitResp = ApiIn "POST" "git/commits" ($body | ConvertTo-Json -Depth 5)
    $newCommit = ($commitResp | ConvertFrom-Json).sha
    if (-not $newCommit) { throw "Commit creation failed for ${Repo}: $commitResp" }

    Invoke-GhApi @("-X", "PATCH", "/repos/$Owner/$Repo/git/refs/heads/$Branch", "-f", "sha=$newCommit") | Out-Null
    Write-Output "COMMITTED ${Owner}/${Repo} -> $newCommit ($($entries.Count) files)"
    } finally { Cleanup }
}
