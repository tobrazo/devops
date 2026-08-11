resource "kubernetes_storage_class" "efs" {
  metadata {
    name = "efs-sc"
  }

  storage_provisioner = "efs.csi.aws.com"

  parameters = {
    provisioningMode = "efs-ap"
    fileSystemId     = module.efs.efs_id
    directoryPerms   = "775"
  }

  reclaim_policy         = "Retain"
  volume_binding_mode    = "Immediate"
  allow_volume_expansion = true

  mount_options = [
    "tls",
    "nfsvers=4.1",
    "hard",
    "timeo=600",
    "retrans=2"
  ]

}
