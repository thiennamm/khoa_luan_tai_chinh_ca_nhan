#requires -Version 7.0
<# Offline tests only: never import Django, load production settings or use a DB client. #>
$ErrorActionPreference = 'Stop'
$tokens = $null
$errors = $null
$file = Join-Path $PSScriptRoot 'backup_postgresql.ps1'
$ast = [Management.Automation.Language.Parser]::ParseFile($file, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'PowerShell parse failed' }
# Import only reviewed function definitions; do NOT run the script entry point.
foreach ($definition in $ast.FindAll({ param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] }, $false)) {
    . ([scriptblock]::Create($definition.Extent.Text))
}
$passed = 0
function Assert-Case { param([bool]$Value) if (-not $Value) { throw 'Offline assertion failed' }; $script:passed++ }
function Assert-Rejected { param([scriptblock]$Action) $rejected=$false; try { & $Action | Out-Null } catch { $rejected=$true }; Assert-Case $rejected }

$secret = ConvertTo-SecureString 'postgresql://test_user:p%3Aa%5Css@dpg-test.oregon-postgres.render.com/test_db' -AsPlainText -Force
$parsed = Read-RenderConnection $secret
Assert-Case ($parsed.Password -eq 'p:a\ss' -and $parsed.Port -eq '5432' -and $parsed.Database -eq 'test_db')
$secret.Dispose()
$fullTls = ConvertTo-SecureString 'postgresql://user:synthetic@dpg-test.oregon-postgres.render.com/db?sslmode=verify-full' -AsPlainText -Force
Assert-Case (Read-RenderConnection $fullTls).VerifyFullRequested
$fullTls.Dispose()
Assert-Case ((ConvertTo-PassfileField 'a:b\c') -eq 'a\:b\\c')
Assert-Rejected { ConvertTo-PassfileField "bad`nline" }
foreach ($bad in @('postgresql://user:pass@dpg-internal/test_db', 'https://user:pass@example.render.com/db',
    'postgresql://user:p%0Aa@example.render.com/db', 'postgresql://user:pass@example.render.com/db?options=bad',
    'postgresql://user:pass@example.render.com/db%3Danything', 'postgresql://user:pass@127.0.0.1/db')) {
    $hidden = ConvertTo-SecureString $bad -AsPlainText -Force
    Assert-Rejected { Read-RenderConnection $hidden }
    $hidden.Dispose()
}
$repo = Split-Path $PSScriptRoot -Parent
Assert-Rejected { New-PrivateBackupDirectory (Join-Path $repo 'backups/test-denied') $repo }
Assert-Rejected { New-PrivateBackupDirectory 'relative/path' $repo }

# Test the child process environment/error envelope with pwsh, NOT pg tools.
$originalPassword = $env:PGPASSWORD
$originalUrl = $env:DATABASE_URL
try {
    $env:PGPASSWORD = 'synthetic-parent-secret'
    $env:DATABASE_URL = 'synthetic-parent-url'
    $reply = Invoke-PgProcess (Join-Path $PSHOME 'pwsh.exe') @('-NoProfile', '-NonInteractive', '-Command',
        'if ($env:PGPASSWORD -or $env:DATABASE_URL) { exit 8 }; Write-Output "isolated"')
    Assert-Case ($reply.ExitCode -eq 0 -and $reply.Output.Trim() -eq 'isolated')
    $reply = Invoke-PgProcess (Join-Path $PSHOME 'pwsh.exe') @('-NoProfile', '-NonInteractive', '-Command',
        '[Console]::Error.WriteLine("synthetic-secret-error-body"); exit 7')
    Assert-Case ($reply.ExitCode -eq 7 -and $reply.HasStderr)
    Assert-Case (($reply | ConvertTo-Json) -notmatch 'synthetic-secret-error-body')
} finally { $env:PGPASSWORD = $originalPassword; $env:DATABASE_URL = $originalUrl }

$qa = Join-Path 'D:\SAO LUU KHOA LUAN' ('task16a-offline-' + [guid]::NewGuid().ToString('N'))
$folder = New-PrivateBackupDirectory $qa $repo
$missingTools = Invoke-PgProcess (Join-Path $PSHOME 'pwsh.exe') @('-NoProfile', '-NonInteractive', '-File',
    $file, '-PgBin', (Join-Path $qa 'not-installed'), '-CheckToolsOnly')
Assert-Case ($missingTools.ExitCode -ne 0 -and [string]::IsNullOrWhiteSpace($missingTools.Output))
$acl = Get-Acl -LiteralPath $folder
Assert-Case $acl.AreAccessRulesProtected
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
Assert-Case (@($acl.Access | Where-Object { $_.AccessControlType -eq 'Allow' -and
    $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -ne $sid }).Count -eq 0)
$fake = Join-Path $folder 'synthetic-not-a-postgres-archive.dump'
[IO.File]::WriteAllText($fake, 'Offline test fixture, NOT a database backup')
$temporaryPass = Join-Path $folder '.pgpass.tmp'
[IO.File]::WriteAllText($temporaryPass, 'SYNTHETIC-PASSFILE-ONLY')
Remove-BackupPassfile $temporaryPass
Assert-Case (-not (Test-Path -LiteralPath $temporaryPass))
Remove-BackupPassfile $temporaryPass
Assert-Case (-not (Test-Path -LiteralPath $temporaryPass))
[IO.File]::WriteAllText($temporaryPass, 'SYNTHETIC-LOCKED-PASSFILE')
$lockedPassfile = [IO.File]::Open($temporaryPass, 'Open', 'ReadWrite', 'None')
try {
    Assert-Rejected { Remove-BackupPassfile $temporaryPass }
    Assert-Case (Test-Path -LiteralPath $temporaryPass)
} finally { $lockedPassfile.Dispose() }
Remove-BackupPassfile $temporaryPass
Assert-Case (-not (Test-Path -LiteralPath $temporaryPass))
$cleanupCall = $ast.FindAll({param($node) $node -is [Management.Automation.Language.CommandAst] -and
    $node.GetCommandName() -eq 'Remove-BackupPassfile'}, $true) | Where-Object { $_.Extent.Text -eq 'Remove-BackupPassfile $passFile' } | Select-Object -First 1
$finalMove = $ast.FindAll({param($node) $node -is [Management.Automation.Language.CommandAst] -and
    $node.GetCommandName() -eq 'Move-Item'}, $true) | Select-Object -First 1
Assert-Case ($null -ne $cleanupCall -and $cleanupCall.Extent.StartOffset -lt $finalMove.Extent.StartOffset)
$script:toolCalls = @()
function Invoke-PgProcess {
    param([string]$Exe, [string[]]$Arguments, [hashtable]$ConnectionEnvironment = @{})
    $script:toolCalls += ,$Arguments
    return @{ ExitCode=0; Output='Synthetic TOC'; HasStderr=$false }
}
$hash = Test-PgArchive 'mock-pg-restore' $fake
Assert-Case ($hash -eq (Get-FileHash -LiteralPath $fake -Algorithm SHA256).Hash.ToLowerInvariant())
Assert-Case ($script:toolCalls.Count -eq 2 -and $script:toolCalls[0][0] -eq '--list' -and
    $script:toolCalls[1] -contains '--file=NUL' -and $script:toolCalls[1] -notcontains '--dbname')
function Invoke-PgProcess { return @{ ExitCode=1; Output=''; HasStderr=$true } }
Assert-Rejected { Test-PgArchive 'mock-pg-restore' $fake }
function Invoke-PgProcess {
    param([string]$Exe, [string[]]$Arguments)
    if ($Arguments[0] -eq '--list') { return @{ ExitCode=0; Output='Synthetic TOC'; HasStderr=$false } }
    return @{ ExitCode=1; Output=''; HasStderr=$true }
}
Assert-Rejected { Test-PgArchive 'mock-pg-restore' $fake }
Write-Output "Offline: $passed assertions passed. Mocked archive stages; NO PostgreSQL connection, dump or restore performed."
Write-Output "Synthetic fixtures only: $qa"
