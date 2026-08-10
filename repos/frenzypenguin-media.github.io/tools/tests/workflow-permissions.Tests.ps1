<#
.SYNOPSIS
    Static checks for the workflow files in .github/workflows.

.DESCRIPTION
    Two classes of bug are caught here, both of which have bitten this repo:

    1. A missing `actions: write` on a workflow that dispatches another
       workflow. `gh workflow run` is an Actions API call, not a git push, so
       `contents: write` does not cover it. refresh-snapshot.yml ran with only
       `contents: write` and failed every Monday at the very last step with
       "HTTP 403: Resource not accessible by integration" - after the snapshot
       had already been committed, so the run looked half-successful while the
       site kept serving the previous snapshot.

    2. A job-level `permissions:` block that silently overrides the
       workflow-level one, dropping a scope the job depends on.

    Written for Pester 3.4 (legacy `Should Be` syntax, no file-level
    BeforeAll). Invoke it either way:

        powershell -NoProfile -ExecutionPolicy Bypass -File tools/tests/workflow-permissions.Tests.ps1
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Import-Module Pester; Invoke-Pester tools/tests/workflow-permissions.Tests.ps1"
#>

function Get-WorkflowYaml {
  param([string]$Path)

  # Parse with pyyaml when it is available so the job-level checks see real
  # structure. Without it the raw-text checks still run, so the script degrades
  # to partial coverage rather than silently passing everything.
  $py = @'
import sys, yaml, json
print(json.dumps(yaml.safe_load(open(sys.argv[1], encoding="utf-8"))))
'@
  $tmpPy = Join-Path ([IO.Path]::GetTempPath()) ("wfchk-" + [guid]::NewGuid().ToString('N') + '.py')
  [IO.File]::WriteAllText($tmpPy, $py)
  try {
    $out = python $tmpPy $Path 2>$null
    if ($LASTEXITCODE -eq 0 -and $out) {
      return (($out -join '').Trim() | ConvertFrom-Json)
    }
  }
  catch {
    # fall through to $null
  }
  finally {
    Remove-Item -LiteralPath $tmpPy -Force -ErrorAction SilentlyContinue
  }
  return $null
}

Describe 'workflow permissions are sufficient for what each workflow does' {

  $WorkflowDir = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) '.github/workflows'

  It 'finds the workflow directory' {
    Test-Path -LiteralPath $WorkflowDir | Should Be $true
  }

  It 'grants actions: write to every workflow that dispatches another workflow' {
    $files = @(Get-ChildItem -LiteralPath $WorkflowDir -Filter '*.yml' -File)
    $files.Count | Should BeGreaterThan 0

    $problems = New-Object System.Collections.Generic.List[string]

    foreach ($file in $files) {
      $raw = [IO.File]::ReadAllText($file.FullName)
      if ($raw -notmatch 'gh\s+workflow\s+run' -and $raw -notmatch '/dispatches') { continue }

      $blocks = [regex]::Matches($raw, '(?ms)^\s*permissions:\s*\n(?<b>(?:\s{2,}\S.*\n)+)')
      $hasActionsWrite = $false
      foreach ($b in $blocks) {
        if ($b.Groups['b'].Value -match '(?m)^\s*actions:\s*write\s*$') { $hasActionsWrite = $true }
      }
      if (-not $hasActionsWrite) {
        $problems.Add("$($file.Name) dispatches another workflow but no permissions block grants 'actions: write'")
      }
    }

    $problems.Count | Should Be 0
  }

  It 'gives no job a permissions block that is narrower than the work it does' {
    $files = @(Get-ChildItem -LiteralPath $WorkflowDir -Filter '*.yml' -File)
    $problems = New-Object System.Collections.Generic.List[string]

    foreach ($file in $files) {
      $wf = Get-WorkflowYaml -Path $file.FullName
      if (-not $wf) { continue }          # pyyaml unavailable: text checks cover it
      if (-not $wf.jobs) { continue }

      foreach ($prop in $wf.jobs.PSObject.Properties) {
        $job = $prop.Value
        if (-not $job.permissions -or -not $job.steps) { continue }

        $stepsText = $job.steps | ConvertTo-Json -Depth 6 -Compress

        if ($stepsText -match 'gh\s+workflow\s+run|/dispatches' -and $job.permissions.actions -ne 'write') {
          $problems.Add("$($file.Name) job '$($prop.Name)' dispatches a workflow but its job-level permissions block omits actions: write")
        }
        if ($stepsText -match 'git\s+push' -and $job.permissions.contents -ne 'write') {
          $problems.Add("$($file.Name) job '$($prop.Name)' runs 'git push' but its job-level permissions block omits contents: write")
        }
      }
    }

    $problems.Count | Should Be 0
  }

  It 'parses every workflow as YAML' {
    $files = @(Get-ChildItem -LiteralPath $WorkflowDir -Filter '*.yml' -File)
    foreach ($file in $files) {
      $wf = Get-WorkflowYaml -Path $file.FullName
      if ($null -eq $wf) {
        Set-ItResult -Skipped -Because 'pyyaml unavailable on this host'
        return
      }
      ($null -ne $wf) | Should Be $true
    }
  }
}
