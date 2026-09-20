$ErrorActionPreference = "Stop"

$jenkins = if ($env:JENKINS_URL) { $env:JENKINS_URL.TrimEnd("/") } else { "http://localhost:8081" }
$job = if ($env:JENKINS_JOB) { $env:JENKINS_JOB } else { "leeward" }
$tokenFile = Join-Path (Split-Path $PSScriptRoot -Parent) ".jenkins-token"
$buildUrl = "$jenkins/job/$job/build"

$user = $env:JENKINS_USER
$token = $env:JENKINS_API_TOKEN
$jobToken = $env:JENKINS_BUILD_TOKEN

if ((-not $user -or -not $token) -and (Test-Path $tokenFile)) {
    $raw = (Get-Content -Raw $tokenFile).Trim()
    if ($raw -match "^(.*?):(.*)$") {
        $user = $Matches[1]
        $token = $Matches[2]
    } else {
        $jobToken = $raw
    }
}

try {
    $headers = @{ "User-Agent" = "buy-the-dip-git-hook" }
    if ($user -and $token) {
        $pair = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${user}:${token}"))
        $headers["Authorization"] = "Basic $pair"
        try {
            $crumb = Invoke-RestMethod -Uri "$jenkins/crumbIssuer/api/json" -Headers $headers
            $headers[$crumb.crumbRequestField] = $crumb.crumb
        } catch {
            # Some Jenkins setups skip crumbs for API tokens.
        }
    }

    if ($jobToken) {
        $buildUrl = "$buildUrl`?token=$([uri]::EscapeDataString($jobToken))"
    }

    Invoke-WebRequest -Uri $buildUrl -Method POST -Headers $headers -UseBasicParsing | Out-Null
    Write-Host "Triggered Jenkins job '$job' against the local working tree."
} catch {
    Write-Host "Jenkins trigger failed: $($_.Exception.Message)"
    Write-Host "Set JENKINS_USER and JENKINS_API_TOKEN, or put user:token in .jenkins-token."
    Write-Host "You can still run the job with Build Now; it tests $PWD locally."
    exit 0
}
