$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36'

$targets = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'hostlist.txt') | Where-Object { $_.Trim() -ne '' }

$rows = foreach ($t in $targets) {
    $t = $t.Trim()
    $entry = [ordered]@{ url = $t; code = 0; status = 'DEAD'; final = ''; note = '' }
    try {
        $req = [Net.HttpWebRequest]::Create($t)
        $req.UserAgent = $UA
        $req.Method = 'GET'
        $req.Timeout = 20000
        $req.ReadWriteTimeout = 20000
        $req.AllowAutoRedirect = $true
        $req.MaximumAutomaticRedirections = 8
        $req.KeepAlive = $false
        $req.Proxy = $null
        $resp = $req.GetResponse()
        $entry.code = [int]$resp.StatusCode
        $entry.final = $resp.ResponseUri.AbsoluteUri
        $entry.status = 'OK'
        $resp.Close()
    } catch [System.Net.WebException] {
        $r = $_.Exception.Response
        if ($r) {
            $entry.code = [int]$r.StatusCode
            try { $entry.final = $r.ResponseUri.AbsoluteUri } catch { }
            if ($entry.code -ge 200 -and $entry.code -lt 400) { $entry.status = 'OK' }
            elseif ($entry.code -in 401, 403, 405, 406, 429, 503) { $entry.status = 'GUARDED'; $entry.note = 'bot/edge protection' }
            else { $entry.status = 'DEAD' }
            $r.Close()
        } else {
            $entry.status = 'DEAD'
            $entry.note = $_.Exception.Message
        }
    } catch {
        $entry.status = 'DEAD'
        $entry.note = $_.Exception.Message
    }
    [pscustomobject]$entry
}

$rows | Export-Csv -LiteralPath (Join-Path $PSScriptRoot 'hostcheck.csv') -NoTypeInformation -Encoding UTF8
$rows | Sort-Object status, url | Format-Table url, status, code, final -AutoSize -Wrap
Write-Output ""
Write-Output ("OK=" + @($rows | Where-Object status -eq 'OK').Count + "  GUARDED=" + @($rows | Where-Object status -eq 'GUARDED').Count + "  DEAD=" + @($rows | Where-Object status -eq 'DEAD').Count)