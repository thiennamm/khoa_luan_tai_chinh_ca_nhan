#requires -Version 7.0
<#
Only -Backup connects to a database. Default mode checks installed tools only.
Secrets are prompted, never accepted as command-line parameters.
#>
[CmdletBinding(DefaultParameterSetName = 'Tools')]
param(
    [Parameter(Mandatory)][string]$PgBin,
    [Parameter(ParameterSetName = 'Tools')][switch]$CheckToolsOnly,
    [Parameter(Mandatory, ParameterSetName = 'Verify')][string]$VerifyArchive,
    [Parameter(Mandatory, ParameterSetName = 'Backup')][switch]$Backup,
    [Parameter(Mandatory, ParameterSetName = 'Backup')][ValidateRange(10, 99)][int]$ServerMajor,
    [Parameter(ParameterSetName = 'Backup')][string]$BackupRoot = 'D:\SAO LUU KHOA LUAN\PostgreSQL',
    [Parameter(ParameterSetName = 'Backup')][string]$SslRootCert
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-PgProcess {
    param([string]$Exe, [string[]]$Arguments, [hashtable]$ConnectionEnvironment = @{})
    $info = [System.Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $Exe
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
    # Never inherit a connection, password, service or libpq override from the shell.
    foreach ($key in @($info.Environment.Keys)) {
        if ($key -like 'PG*' -or $key -eq 'DATABASE_URL') { [void]$info.Environment.Remove($key) }
    }
    foreach ($key in $ConnectionEnvironment.Keys) { $info.Environment[$key] = $ConnectionEnvironment[$key] }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $info
    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        # Native errors can contain host/user/database or SQL: never return their body.
        return @{ ExitCode = $process.ExitCode; Output = $stdout.GetAwaiter().GetResult();
            HasStderr = -not [string]::IsNullOrWhiteSpace($stderr.GetAwaiter().GetResult()) }
    } finally { $process.Dispose() }
}

function Read-RenderConnection {
    param([securestring]$SecretUrl)
    $pointer = [IntPtr]::Zero
    try {
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecretUrl)
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        $uri = [Uri]::new($plain, [UriKind]::Absolute)
        if ($uri.Scheme -notin @('postgres', 'postgresql') -or
            -not $uri.Host.EndsWith('.render.com', [StringComparison]::OrdinalIgnoreCase) -or
            $uri.Fragment -or $uri.Query -notin @('', '?sslmode=require', '?sslmode=verify-full')) {
            throw 'Invalid connection'
        }
        $colon = $uri.UserInfo.IndexOf(':')
        if ($colon -lt 1) { throw 'Missing credential' }
        $login = [Uri]::UnescapeDataString($uri.UserInfo.Substring(0, $colon))
        $password = [Uri]::UnescapeDataString($uri.UserInfo.Substring($colon + 1))
        $database = [Uri]::UnescapeDataString($uri.AbsolutePath.TrimStart('/'))
        if ($login -notmatch '^[A-Za-z0-9_][A-Za-z0-9_.-]*$' -or
            $database -notmatch '^[A-Za-z0-9_][A-Za-z0-9_.-]*$' -or
            [string]::IsNullOrEmpty($password) -or $password -match '[\r\n\x00]') {
            throw 'Invalid credential fields'
        }
        $port = if ($uri.Port -eq -1) { 5432 } else { $uri.Port }
        if ($port -lt 1 -or $port -gt 65535) { throw 'Invalid port' }
        return @{ Host = $uri.Host; Port = "$port"; Database = $database; User = $login; Password = $password;
            VerifyFullRequested = ($uri.Query -eq '?sslmode=verify-full') }
    } catch { throw 'CONNECTION_INPUT_INVALID' }
    finally {
        if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
        $plain = $null
    }
}

function ConvertTo-PassfileField {
    param([string]$Value)
    if ($Value -match '[\r\n\x00]') { throw 'PASSFILE_FIELD_INVALID' }
    return $Value.Replace('\', '\\').Replace(':', '\:')
}

function New-PrivateBackupDirectory {
    param([string]$Root, [string]$Repository)
    if (-not [IO.Path]::IsPathFullyQualified($Root)) { throw 'BACKUP_PATH_NOT_ABSOLUTE' }
    $resolved = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $repo = [IO.Path]::GetFullPath($Repository).TrimEnd('\', '/')
    if ($resolved.Equals($repo, [StringComparison]::OrdinalIgnoreCase) -or
        $resolved.StartsWith($repo + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'BACKUP_INSIDE_REPOSITORY' }
    # Do not accept junction/symlink ancestors that could redirect the destination.
    $ancestor = [IO.DirectoryInfo]::new($resolved)
    while ($null -ne $ancestor) {
        if ($ancestor.Exists -and ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'BACKUP_REPARSE_POINT' }
        $ancestor = $ancestor.Parent
    }
    [void][IO.Directory]::CreateDirectory($resolved)
    $name = 'postgres-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
    $folder = Join-Path $resolved $name
    if (Test-Path -LiteralPath $folder) { throw 'BACKUP_ALREADY_EXISTS' }
    [void][IO.Directory]::CreateDirectory($folder)
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetOwner($identity)
    $acl.SetAccessRuleProtection($true, $false)
    $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity, 'FullControl',
        'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $folder -AclObject $acl
    return $folder
}

function Test-PgArchive {
    param([string]$RestoreExe, [string]$Archive)
    if (-not (Test-Path -LiteralPath $Archive -PathType Leaf)) { throw 'ARCHIVE_MISSING' }
    if ((Get-Item -LiteralPath $Archive).Length -eq 0) { throw 'ARCHIVE_EMPTY' }
    $toc = Invoke-PgProcess $RestoreExe @('--list', $Archive)
    if ($toc.ExitCode -ne 0 -or $toc.HasStderr -or [string]::IsNullOrWhiteSpace($toc.Output)) { throw 'ARCHIVE_TOC_FAILED' }
    # No --dbname: decode SQL/data to Windows NUL, do not execute it or store plain SQL.
    $decode = Invoke-PgProcess $RestoreExe @('--exit-on-error', '--file=NUL', $Archive)
    if ($decode.ExitCode -ne 0 -or $decode.HasStderr) { throw 'ARCHIVE_DECODE_FAILED' }
    return (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Remove-BackupPassfile {
    param([string]$Path)
    try {
        if ($Path -and (Test-Path -LiteralPath $Path)) { Remove-Item -LiteralPath $Path -Force }
        if ($Path -and (Test-Path -LiteralPath $Path)) { throw 'Passfile still exists' }
    } catch { throw 'PASSFILE_CLEANUP_FAILED' }
}

$stage = 'tool-check'
$passFile = $null
$secretUrl = $null
$connection = $null
try {
    if (-not $IsWindows) { throw 'WINDOWS_REQUIRED' }
    if (-not [IO.Path]::IsPathFullyQualified($PgBin)) { throw 'TOOLS_ABSOLUTE_PATH_REQUIRED' }
    $versions = @{}
    foreach ($tool in @('pg_dump', 'pg_restore', 'psql')) {
        $exe = Join-Path $PgBin ($tool + '.exe')
        if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'TOOLS_MISSING' }
        $answer = Invoke-PgProcess $exe @('--version')
        if ($answer.ExitCode -ne 0 -or $answer.Output -notmatch 'PostgreSQL\)\s+(\d+)\.') { throw 'TOOLS_VERSION_UNKNOWN' }
        $versions[$tool] = @{ Version = $answer.Output.Trim(); Major = [int]$Matches[1] }
    }
    if (@($versions.Values | ForEach-Object { $_.Major } | Select-Object -Unique).Count -ne 1) { throw 'TOOLS_VERSION_MISMATCH' }
    if ($PSCmdlet.ParameterSetName -eq 'Tools') {
        foreach ($tool in @('pg_dump', 'pg_restore', 'psql')) { Write-Output $versions[$tool].Version }
        Write-Output 'Chỉ kiểm công cụ local; chưa kết nối database.'
        return
    }
    if ($PSCmdlet.ParameterSetName -eq 'Verify') {
        $stage = 'archive-read'
        $hash = Test-PgArchive (Join-Path $PgBin 'pg_restore.exe') ([IO.Path]::GetFullPath($VerifyArchive))
        Write-Output "Archive đọc/giải mã được. SHA-256: $hash. CHƯA chứng minh phục hồi thành công."
        return
    }
    if ($versions['pg_dump'].Major -ne $ServerMajor) { throw 'CLIENT_MAJOR_MUST_MATCH_DASHBOARD' }
    $stage = 'secret-input'
    $secretUrl = Read-Host 'Dán External Database URL của Render (ẩn; không dán Internal URL)' -AsSecureString
    $connection = Read-RenderConnection $secretUrl
    if ($connection.VerifyFullRequested -and -not $SslRootCert) { throw 'ROOT_CERT_REQUIRED_FOR_VERIFY_FULL' }
    $stage = 'private-directory'
    $folder = New-PrivateBackupDirectory $BackupRoot (Split-Path $PSScriptRoot -Parent)
    $passFile = Join-Path $folder '.pgpass.tmp'
    $line = (@($connection.Host, $connection.Port, $connection.Database, $connection.User, $connection.Password) |
        ForEach-Object { ConvertTo-PassfileField $_ }) -join ':'
    [IO.File]::WriteAllText($passFile, $line + "`n", [Text.UTF8Encoding]::new($false))
    $line = $null
    $connection.Password = $null
    $envForChild = @{ PGHOST = $connection.Host; PGPORT = $connection.Port; PGDATABASE = $connection.Database;
        PGUSER = $connection.User; PGPASSFILE = $passFile; PGSSLMODE = 'require'; PGCONNECT_TIMEOUT = '15';
        PGAPPNAME = 'so-thu-chi-manual-backup'; PGOPTIONS = '-c default_transaction_read_only=on' }
    if ($SslRootCert) {
        if (-not (Test-Path -LiteralPath $SslRootCert -PathType Leaf)) { throw 'ROOT_CERT_MISSING' }
        $envForChild.PGSSLMODE = 'verify-full'
        $envForChild.PGSSLROOTCERT = [IO.Path]::GetFullPath($SslRootCert)
    }
    $stage = 'server-version-readonly'
    $server = Invoke-PgProcess (Join-Path $PgBin 'psql.exe') @('-X', '--no-password', '--tuples-only', '--no-align', '--command', 'SHOW server_version_num;') $envForChild
    if ($server.ExitCode -ne 0 -or $server.HasStderr -or $server.Output.Trim() -notmatch '^\d+$') { throw 'SERVER_VERSION_FAILED' }
    if ([math]::Floor([int]$server.Output.Trim() / 10000) -ne $ServerMajor) { throw 'SERVER_MAJOR_CHANGED' }
    $stage = 'pg-dump'
    $archiveName = (Split-Path $folder -Leaf) + '.dump'
    $partial = Join-Path $folder ($archiveName + '.partial')
    $started = [DateTime]::UtcNow.ToString('o')
    $dump = Invoke-PgProcess (Join-Path $PgBin 'pg_dump.exe') @('--format=custom', '--no-password', '--lock-wait-timeout=30s', '--file', $partial) $envForChild
    if ($dump.ExitCode -ne 0 -or $dump.HasStderr) { throw 'DUMP_FAILED_OR_WARNINGS' }
    $stage = 'archive-read'
    $hash = Test-PgArchive (Join-Path $PgBin 'pg_restore.exe') $partial
    # Do not publish a successful archive/manifest while a temporary password remains.
    $stage = 'credential-cleanup'
    Remove-BackupPassfile $passFile
    $passFile = $null
    $stage = 'archive-finalize'
    $archive = Join-Path $folder $archiveName
    Move-Item -LiteralPath $partial -Destination $archive
    $manifest = @{ format = 'PostgreSQL custom archive'; started_at_utc = $started; finished_at_utc = [DateTime]::UtcNow.ToString('o');
        archive = $archiveName; bytes = (Get-Item -LiteralPath $archive).Length; sha256 = $hash;
        client_versions = $versions; server_version_num = $server.Output.Trim(); tls_mode = $envForChild.PGSSLMODE;
        archive_list_and_decode = 'passed'; restore_into_qa = 'NOT_PERFORMED'; tool = 'backup_postgresql.ps1-v1' }
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $folder 'manifest.json') -Encoding utf8
    Write-Output "Đã sao lưu: $folder"
    Write-Output "SHA-256: $hash. Archive đọc được; CHƯA phục hồi thử."
} catch {
    # Never expose $_, native stderr, connection URL, credentials or response bodies.
    throw "Chưa hoàn tất. Giai đoạn: $stage. Kiểm đường dẫn/phiên bản/quyền/TLS theo tài liệu; không chia sẻ secret hoặc lỗi gốc."
} finally {
    if ($passFile -and (Test-Path -LiteralPath $passFile)) {
        try { Remove-BackupPassfile $passFile }
        catch { Write-Warning 'Không xóa được tệp mật khẩu tạm trong thư mục backup riêng tư. Xóa .pgpass.tmp trước khi sao chép thư mục; không chia sẻ nội dung.' }
    }
    if ($null -ne $secretUrl) { $secretUrl.Dispose() }
    $connection = $null
}
