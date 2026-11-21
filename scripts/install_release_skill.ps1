<#
.SYNOPSIS
Install one Wisconsin skill ZIP using SHA256SUMS.txt from the same GitHub release.
#>
param(
    [Parameter(Mandatory)][string]$Archive,
    [Parameter(Mandatory)][string]$SkillsDirectory
)
$ErrorActionPreference = 'Stop'
$zip = Get-Item -LiteralPath $Archive
$name = $zip.BaseName
if ($zip.Name -cnotin @('cite-check.zip', 'wisconsin-legal-writing.zip', 'wisconsin-legal-interpretation.zip')) {
    throw "Choose one of the three individual skill ZIPs from the release."
}
$root = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($SkillsDirectory)
$destination = Join-Path $root $name
if (Test-Path -LiteralPath $destination) {
    throw "Already installed at $destination. Choose an empty location to compare versions."
}
$manifest = Join-Path $zip.DirectoryName 'SHA256SUMS.txt'
$pattern = '^([a-fA-F0-9]{64})  ' + [regex]::Escape($zip.Name) + '$'
$entries = @(Get-Content -LiteralPath $manifest | Where-Object { $_ -cmatch $pattern })
if ($entries.Count -ne 1) { throw "Expected one checksum for $($zip.Name) in $manifest." }

# Put the temporary copy beside the host's skills directory so discovery cannot see a partial skill.
$parent = [IO.Directory]::CreateDirectory((Split-Path -Parent $root)).FullName
$stage = Join-Path $parent ('.wi-skill-' + [guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($stage)
try {
    $copy = Join-Path $stage $zip.Name
    [IO.File]::Copy($zip.FullName, $copy)
    if ((Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash -ne $entries[0].Substring(0, 64)) {
        throw "Checksum mismatch for $($zip.Name). Download the ZIP and checksums from the same release."
    }
    $unpacked = Join-Path $stage 'unpacked'
    Expand-Archive -LiteralPath $copy -DestinationPath $unpacked
    $skill = Join-Path $unpacked $name
    if (-not [IO.File]::Exists((Join-Path $skill 'SKILL.md'))) { throw "Missing $name/SKILL.md." }
    $null = [IO.Directory]::CreateDirectory($root)
    [IO.Directory]::Move($skill, $destination)
    Write-Output "Verified $($zip.Name) and installed it at $destination"
} finally {
    # Only the fresh, individually named staging directory is owned by this invocation.
    $resolved = [IO.Path]::GetFullPath($stage)
    if ((Split-Path -Parent $resolved) -eq $parent -and (Split-Path -Leaf $resolved) -match '^\.wi-skill-[0-9a-f]{32}$') {
        [IO.Directory]::Delete($resolved, $true)
    }
}
