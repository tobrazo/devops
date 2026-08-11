########################################
# envs/management/main.tf
# Windows Server 2022 EC2 + PostgreSQL 16 + RDP
# Region: eu-central-1 (Frankfurt)
########################################

terraform {
  backend "s3" {
    bucket         = "tobrazo-terraform-state"
    key            = "management/terraform.tfstate" # unique key — prod uses prod/terraform.tfstate
    region         = "eu-central-1"
    dynamodb_table = "tobrazo-terraform-lock"
    encrypt        = true
  }
}

########################################
# Latest Windows Server 2022 AMI (official AWS)
########################################

data "aws_ami" "windows_2022" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Windows_Server-2022-English-Full-Base-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

########################################
# IAM instance profile (SSM access — no need to open SSH)
########################################

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "windows" {
  name               = "${local.name_prefix}-windows-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.windows.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "windows" {
  name = "${local.name_prefix}-windows-profile"
  role = aws_iam_role.windows.name
}

########################################
# EC2 Windows + PostgreSQL 16 (via Chocolatey)
########################################

resource "aws_instance" "windows" {
  ami                    = data.aws_ami.windows_2022.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.windows.id]
  iam_instance_profile   = aws_iam_instance_profile.windows.name

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size_gb
    delete_on_termination = true
    encrypted             = true
    tags                  = merge(local.tags, { Name = "${local.name_prefix}-windows-root" })
  }

  # PowerShell bootstrap: set Admin password → Chocolatey → PostgreSQL 16 → configure
  user_data = <<-USERDATA
    <powershell>
    $ErrorActionPreference = "Stop"

    # ── 0. Set Administrator password ─────────────────────────────────────
    $adminPass = ConvertTo-SecureString "${var.windows_admin_password}" -AsPlainText -Force
    Set-LocalUser -Name "Administrator" -Password $adminPass
    # Make sure Administrator account is enabled
    Enable-LocalUser -Name "Administrator"

    # ── 1. Install Chocolatey ──────────────────────────────────────────────
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    # ── 2. Install PostgreSQL 16 ───────────────────────────────────────────
    choco install postgresql16 --confirm `
      --params "'/Password:${var.postgres_password} /Port:5432 /ServiceName:postgresql-x64-16'"

    # ── 3. Add psql to PATH ────────────────────────────────────────────────
    $pgBin = "C:\Program Files\PostgreSQL\16\bin"
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    if ($currentPath -notlike "*$pgBin*") {
      [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$pgBin", "Machine")
    }
    $env:Path += ";$pgBin"
    $env:PGPASSWORD = "${var.postgres_password}"

    # ── 4. Allow PostgreSQL to listen on all interfaces ───────────────────
    $pgData = "C:\Program Files\PostgreSQL\16\data"
    $pgConf = "$pgData\postgresql.conf"
    (Get-Content $pgConf) `
      -replace "#?listen_addresses\s*=\s*'localhost'", "listen_addresses = '*'" |
      Set-Content $pgConf

    # ── 5. Allow password-auth from any IP in pg_hba.conf ─────────────────
    # Access is controlled by the Security Group — pg_hba is a second layer
    Add-Content "$pgData\pg_hba.conf" "host  all  all  0.0.0.0/0  scram-sha-256"

    # ── 6. Set up data disk (D:\pgdata) ───────────────────────────────────
    # Wait up to 2 min for the EBS volume to appear
    $timeout = 120
    $pgVol = $null
    while (-not $pgVol -and $timeout -gt 0) {
      $pgVol = Get-Volume -FileSystemLabel "pgdata" -ErrorAction SilentlyContinue
      if (-not $pgVol) { Start-Sleep 5; $timeout -= 5 }
    }

    if (-not $pgVol) {
      # New raw disk — initialize, format as D:, label "pgdata"
      $rawDisk = Get-Disk | Where-Object { $_.PartitionStyle -eq 'RAW' } | Select-Object -First 1
      if ($rawDisk) {
        $rawDisk | Initialize-Disk -PartitionStyle GPT -PassThru |
          New-Partition -DriveLetter D -UseMaximumSize |
          Format-Volume -FileSystem NTFS -NewFileSystemLabel "pgdata" -Confirm:$false
        $pgVol = Get-Volume -FileSystemLabel "pgdata"
      }
    }

    if ($pgVol) {
      $driveLetter = $pgVol.DriveLetter
      $pgDst = "$${driveLetter}:\pgdata"

      if (-not (Test-Path $pgDst)) {
        # First time: move pgdata from C: to data disk
        Stop-Service "postgresql-x64-16" -Force
        Copy-Item "C:\Program Files\PostgreSQL\16\data" $pgDst -Recurse -Force
      }
      # (else: disk already has data from a previous instance — reuse it as-is)

      # Grant NetworkService full control on the data directory
      icacls $pgDst /grant "NT AUTHORITY\NetworkService:(OI)(CI)F" /T | Out-Null

      # Point the Windows service to the correct data directory
      $svcKey = "HKLM:\SYSTEM\CurrentControlSet\Services\postgresql-x64-16"
      $imgPath = (Get-ItemProperty $svcKey).ImagePath
      $newImg = $imgPath -replace '-D "[^"]*"', "-D `"$pgDst`""
      Set-ItemProperty $svcKey -Name ImagePath -Value $newImg
    }

    # ── 7. Restart PostgreSQL service ─────────────────────────────────────
    Restart-Service -Name "postgresql-x64-16" -Force

    # ── 8. Windows Firewall rules (belt-and-suspenders, SG is the real gate)
    New-NetFirewallRule -DisplayName "PostgreSQL 5432" `
      -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow -Profile Any | Out-Null

    Write-Output "Bootstrap complete: PostgreSQL 16 installed and running."
    </powershell>
  USERDATA

  tags = merge(local.tags, { Name = "${local.name_prefix}-windows" })

  lifecycle {
    ignore_changes = [
      # AMI will change as AWS releases patches — don't redeploy on every plan
      ami,
      # user_data is only applied at first boot; ignore drift
      user_data,
    ]
  }
}

########################################
# Elastic IP — stable RDP address
########################################

resource "aws_eip" "windows" {
  instance = aws_instance.windows.id
  domain   = "vpc"
  tags     = merge(local.tags, { Name = "${local.name_prefix}-windows-eip" })
}

########################################
# EBS data volume — PostgreSQL data dir (D:\pgdata)
# delete_on_termination = false by default for standalone volumes
# → survives instance stop/replace/termination
########################################

resource "aws_ebs_volume" "pgdata" {
  availability_zone = "${var.region}a"
  size              = var.pgdata_volume_size_gb
  type              = "gp3"
  encrypted         = true

  tags = merge(local.tags, { Name = "${local.name_prefix}-pgdata" })

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_volume_attachment" "pgdata" {
  device_name  = "/dev/sdf"
  volume_id    = aws_ebs_volume.pgdata.id
  instance_id  = aws_instance.windows.id
  force_detach = false
}
