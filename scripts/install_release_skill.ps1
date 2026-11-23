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
    throw "Choose one of the three individual skill ZIPs with its original release filename. Received '$($zip.Name)'."
}
$provider = $drive = $null
$path = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($SkillsDirectory, [ref]$provider, [ref]$drive)
if ($provider.Name -ne 'FileSystem') { throw "Choose a local filesystem directory." }
$root = [IO.DirectoryInfo]::new($path)
$parent = $root.Parent
if (-not $parent) { throw "Choose a skills folder below a volume root." }
$destination = [IO.Path]::Combine($root.FullName, $name)
for ($dir = $root; $dir; $dir = $dir.Parent) {
    $attributes = $dir.Attributes
    if ($attributes -ne -1 -and ($attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Choose a local skills path without a link or junction: $($dir.FullName)"
    }
}
if (Test-Path -LiteralPath $destination) {
    throw "Already installed at $destination. Choose a separate location to compare versions."
}
$manifest = [IO.Path]::Combine($zip.DirectoryName, 'SHA256SUMS.txt')
$pattern = '^([a-fA-F0-9]{64})  ' + [regex]::Escape($zip.Name) + '$'
$entries = @([IO.File]::ReadAllLines($manifest) -cmatch $pattern)
if ($entries.Count -ne 1) { throw "Expected one checksum for $($zip.Name) in $manifest." }

# Stage outside discovery, in an existing ancestor, even for the first installation.
$stageParent = $parent
while ($stageParent -and -not $stageParent.Exists) { $stageParent = $stageParent.Parent }
if (-not $stageParent) { throw "No accessible parent directory for $SkillsDirectory." }
$stagePath = [IO.Path]::Combine($stageParent.FullName, '.wi-skill-' + [guid]::NewGuid().ToString('N'))
$stage = New-Item -ItemType Directory -Path $stagePath
if ($stage -isnot [IO.DirectoryInfo] -or $stage.FullName -cne $stagePath) { throw "Could not create the staging directory." }
try {
    $copy = [IO.Path]::Combine($stage.FullName, $zip.Name)
    [IO.File]::Copy($zip.FullName, $copy)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    Add-Type -AssemblyName System.IO.Compression
    $stream = [IO.File]::OpenRead($copy)
    try {
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $digest = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') }
        finally { $sha.Dispose() }
        if ($digest -ne $entries[0].Substring(0, 64)) {
            throw "Checksum mismatch for $($zip.Name). Download the ZIP and checksums from the same release."
        }
        $stream.Position = 0
        $package = [IO.Compression.ZipArchive]::new($stream, [IO.Compression.ZipArchiveMode]::Read)
        try {
            $unpacked = [IO.Path]::Combine($stage.FullName, 'unpacked')
            [IO.Compression.ZipFileExtensions]::ExtractToDirectory($package, $unpacked)
        } finally { $package.Dispose() }
    } finally { $stream.Dispose() }
    $skill = [IO.Path]::Combine($unpacked, $name)
    if (-not [IO.File]::Exists([IO.Path]::Combine($skill, 'SKILL.md'))) { throw "Missing $name/SKILL.md." }
    $null = [IO.Directory]::CreateDirectory($root.FullName)
    [IO.Directory]::Move($skill, $destination)
} finally {
    $owned = [IO.DirectoryInfo]::new([IO.Path]::GetFullPath($stage.FullName))
    if ($owned.Parent.FullName -cne $stageParent.FullName -or $owned.Name -cnotmatch '^\.wi-skill-[0-9a-f]{32}$' -or
        ($owned.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Unexpected staging path. Cleanup stopped." }
    [IO.Directory]::Delete($owned.FullName, $true)
}
Write-Output "Verified $($zip.Name) and installed it at $destination"
