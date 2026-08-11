<div align="center">

# ☁️ AWS EKS Platform (Terraform)

**A production-grade EKS landing zone as code — VPC, managed EKS, EFS, IRSA, and platform add-ons.**

![Terraform](https://img.shields.io/badge/Terraform-1.5+-7B42BC?style=flat-square&logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-EKS-FF9900?style=flat-square&logo=amazonwebservices&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-EKS-326CE5?style=flat-square&logo=kubernetes&logoColor=white)
![Helm](https://img.shields.io/badge/Helm-add--ons-0F1689?style=flat-square&logo=helm&logoColor=white)
![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-EF7B4D?style=flat-square&logo=argo&logoColor=white)

</div>

---

Infrastructure as Code for a production EKS environment on AWS: VPC, EKS cluster, EFS storage, IRSA roles, and platform add-ons (ArgoCD, ingress-nginx, cluster-autoscaler, external-dns, cert-manager, kube-prometheus, Loki).

> [!IMPORTANT]
> This is a **template**. Copy each `*.tfvars.example` to a real (gitignored) `*.tfvars` and fill in your own values — AWS account, region, backend bucket/table, domains, and secrets. Nothing here contains a live credential.

---

## Infrastructure Overview

```mermaid
flowchart TB

subgraph aws["AWS (eu-central-1)"]
  subgraph vpc["VPC 10.0.0.0/16"]
    subgraph public["Public Subnets"]
      alb[Application Load Balancer]
      nat[NAT Gateway]
    end
    subgraph private["Private Subnets (3 AZs)"]
      subgraph eks["EKS Cluster"]
        cp[Control Plane<br/>HA Managed]
        subgraph workers["Node Group"]
          node1[m5.xlarge]
          node2[m5.xlarge]
          nodeN[... auto-scale]
        end
      end
      efs[(EFS<br/>Encrypted Storage)]
    end
  end

  s3[(S3 Bucket<br/>TF State)]
  dynamo[(DynamoDB<br/>State Lock)]
  secrets[(Secrets Manager)]
  kms[KMS<br/>Encryption Keys]
end

subgraph external["External Services"]
  cloudflare[Cloudflare<br/>DNS + CDN]
  ghcr[GHCR<br/>Container Images]
  users[Users]
end

users -->|HTTPS| cloudflare
cloudflare -->|proxy| alb
alb --> eks
nat -.->|egress| ghcr
eks -->|mount| efs
eks -.->|secrets| secrets
efs -.->|encrypt| kms

classDef cluster stroke:#3b82f6,stroke-width:2px;
classDef storage stroke:#8b5cf6,stroke-width:2px;
classDef network stroke:#10b981,stroke-width:2px;
classDef external stroke:#f59e0b,stroke-width:2px;
classDef security stroke:#ef4444,stroke-width:2px;

class cp,node1,node2,nodeN cluster;
class efs,s3,dynamo,secrets storage;
class alb,nat network;
class cloudflare,ghcr,users external;
class kms security;

style aws fill:transparent,stroke:#475569,stroke-width:1.2px;
style vpc fill:transparent,stroke:#3b82f6,stroke-dasharray:6 4,stroke-width:1.2px;
style public fill:transparent,stroke:#10b981,stroke-dasharray:3 3,stroke-width:1px;
style private fill:transparent,stroke:#334155,stroke-dasharray:3 3,stroke-width:1px;
style eks fill:transparent,stroke:#3b82f6,stroke-dasharray:3 3,stroke-width:1px;
style workers fill:transparent,stroke:#334155,stroke-dasharray:3 3,stroke-width:1px;
style external fill:transparent,stroke:#f59e0b,stroke-dasharray:3 3,stroke-width:1px;

linkStyle default stroke:#8b9bab,stroke-width:2px;
```

---

## Module Architecture

```mermaid
flowchart LR

subgraph tf["Terraform Root"]
  main[main.tf]
  locals[locals.tf]
  vars[variables.tf]
  providers[providers.tf]
end

subgraph modules["Modules"]
  vpc_mod[terraform-aws-modules/vpc]
  eks_mod[terraform-aws-modules/eks]
  efs_mod[storage/efs]
  irsa_mod[irsa]
  sg_mod[security-groups]
  iam_admin[iam-admin-role]
  iam_node[iam-node-role]
end

subgraph helm_mods["Helm Modules"]
  argocd[helm/argocd]
  ingress[helm/ingress-nginx]
  autoscaler[helm/cluster-autoscaler]
  ext_dns[helm/external-dns]
  metrics[helm/metrics-server]
  prometheus[helm/kube-prometheus]
  loki[helm/loki-stack]
end

subgraph outputs["Outputs"]
  cluster_name[cluster_name]
  cluster_endpoint[cluster_endpoint]
  oidc_arn[oidc_provider_arn]
end

main --> vpc_mod
main --> eks_mod
main --> efs_mod
main --> irsa_mod
main --> sg_mod

vpc_mod -->|vpc_id| eks_mod
vpc_mod -->|subnets| efs_mod
eks_mod -->|oidc| irsa_mod
eks_mod -->|sg| efs_mod

eks_mod --> argocd
eks_mod --> ingress
eks_mod --> autoscaler
eks_mod --> ext_dns

eks_mod --> cluster_name
eks_mod --> cluster_endpoint
eks_mod --> oidc_arn

classDef tf stroke:#8b5cf6,stroke-width:2px;
classDef mod stroke:#3b82f6,stroke-width:2px;
classDef helm stroke:#10b981,stroke-width:2px;
classDef out stroke:#f59e0b,stroke-width:2px;

class main,locals,vars,providers tf;
class vpc_mod,eks_mod,efs_mod,irsa_mod,sg_mod,iam_admin,iam_node mod;
class argocd,ingress,autoscaler,ext_dns,metrics,prometheus,loki helm;
class cluster_name,cluster_endpoint,oidc_arn out;

style tf fill:transparent,stroke:#8b5cf6,stroke-dasharray:6 4,stroke-width:1.2px;
style modules fill:transparent,stroke:#3b82f6,stroke-dasharray:3 3,stroke-width:1px;
style helm_mods fill:transparent,stroke:#10b981,stroke-dasharray:3 3,stroke-width:1px;
style outputs fill:transparent,stroke:#f59e0b,stroke-dasharray:3 3,stroke-width:1px;

linkStyle default stroke:#8b9bab,stroke-width:2px;
```

---

## What This Deploys

| Resource | Configuration | Details |
|----------|---------------|---------|
| VPC | `10.0.0.0/16` | 3 AZs, public + private subnets |
| EKS Cluster | Managed control plane | K8s with OIDC for IRSA |
| Node Group | `m5.xlarge` | Auto-scaling worker nodes |
| EFS | Encrypted, multi-AZ | Shared storage with CSI driver |
| NAT Gateway | Single (cost-optimized) | Egress for private subnets |
| Security Groups | Node + ALB isolation | VPC-scoped ingress/egress rules |
| IRSA Roles | EFS CSI, Grafana, External Secrets | Pod-level IAM permissions |
| ArgoCD | Helm chart | GitOps controller |
| Ingress NGINX | Helm chart | ALB-backed ingress controller |
| Cluster Autoscaler | Helm chart | Node auto-scaling |
| External DNS | Helm chart | Cloudflare DNS automation |
| cert-manager | Helm chart | TLS certificate automation |

---

## Prerequisites

- Terraform >= 1.5
- AWS account with appropriate IAM permissions
- S3 bucket + DynamoDB table for state backend
- Cloudflare API tokens (external-dns, cert-manager)
- GHCR credentials for image pulls

---

## Directory Layout

```text
aws-eks-platform/
├── envs/
│   └── prod/
│       ├── main.tf              # Root composition
│       ├── locals.tf            # Environment defaults
│       ├── variables.tf         # Input variables
│       ├── outputs.tf           # Cluster outputs
│       ├── providers.tf         # AWS/K8s/Helm providers
│       ├── vpc.tf               # VPC module invocation
│       ├── k8s-post.tf          # Post-deploy K8s resources
│       ├── secrets.tf           # K8s secrets configuration
│       ├── aws-lb-controller.tf # ALB controller setup
│       ├── cluster-autoscaler.tf
│       └── terraform.tfvars.example  # copy -> terraform.tfvars (gitignored)
├── global-backend/
│   ├── main.tf                  # S3 + DynamoDB for state
│   └── variables.tf
└── modules/
    ├── storage/efs/             # EFS file system + mount targets
    ├── irsa/                    # IAM roles for service accounts
    ├── iam-admin-role/          # Admin assume-role
    ├── iam-node-role/           # Node instance profile
    ├── security-groups/         # VPC security groups
    │   └── alb/                 # ALB-specific rules
    └── helm/
        ├── argocd/              # ArgoCD Helm values
        ├── ingress-nginx/       # Ingress controller
        ├── cluster-autoscaler/  # Node autoscaler
        ├── external-dns/        # DNS automation
        ├── kubernetes-metrics-server/
        ├── kube-prometheus/     # Monitoring stack
        ├── loki-stack/          # Log aggregation
        └── aws-lb-controller/   # AWS LB controller
```

---

## Workflow

```mermaid
flowchart LR

init[terraform init]
validate[terraform validate]
plan[terraform plan]
apply[terraform apply]
state[(S3 + DynamoDB<br/>State Backend)]

init -->|configure backend| validate
validate --> plan
plan -->|review| apply
apply -->|store| state

classDef cmd stroke:#3b82f6,stroke-width:2px;
classDef storage stroke:#8b5cf6,stroke-width:2px;

class init,validate,plan,apply cmd;
class state storage;

linkStyle default stroke:#8b9bab,stroke-width:2px;
```

```bash
# Navigate to environment
cd aws-eks-platform/envs/prod

# Initialize backend
terraform init

# Validate configuration
terraform validate

# Plan changes
terraform plan -out=tfplan

# Apply changes
terraform apply tfplan
```

---

## IRSA (IAM Roles for Service Accounts)

```mermaid
flowchart LR

subgraph eks["EKS Cluster"]
  oidc[OIDC Provider]
  sa_efs[efs-csi-controller-sa]
  sa_grafana[grafana]
  sa_secrets[external-secrets-sa]
end

subgraph iam["IAM"]
  role_efs[irsa-efs-csi-driver]
  role_grafana[irsa-grafana]
  role_secrets[irsa-external-secrets]
end

subgraph aws_svc["AWS Services"]
  efs[(EFS)]
  cw[(CloudWatch)]
  sm[(Secrets Manager)]
end

oidc -->|trust| role_efs
oidc -->|trust| role_grafana
oidc -->|trust| role_secrets

sa_efs -.->|assume| role_efs
sa_grafana -.->|assume| role_grafana
sa_secrets -.->|assume| role_secrets

role_efs -->|access| efs
role_grafana -->|read| cw
role_secrets -->|read/write| sm

classDef k8s stroke:#3b82f6,stroke-width:2px;
classDef iam stroke:#f59e0b,stroke-width:2px;
classDef aws stroke:#10b981,stroke-width:2px;

class oidc,sa_efs,sa_grafana,sa_secrets k8s;
class role_efs,role_grafana,role_secrets iam;
class efs,cw,sm aws;

style eks fill:transparent,stroke:#3b82f6,stroke-dasharray:6 4,stroke-width:1.2px;
style iam fill:transparent,stroke:#f59e0b,stroke-dasharray:3 3,stroke-width:1px;
style aws_svc fill:transparent,stroke:#10b981,stroke-dasharray:3 3,stroke-width:1px;

linkStyle default stroke:#8b9bab,stroke-width:2px;
```

| Service Account | IAM Role | Permissions |
|-----------------|----------|-------------|
| `efs-csi-controller-sa` | `irsa-efs-csi-driver` | EFS create/delete access points |
| `grafana` | `irsa-grafana` | CloudWatch metrics/logs read |
| `external-secrets-sa` | `irsa-external-secrets` | Secrets Manager read/write |

---

## Configuration

Key inputs in `terraform.tfvars` and `locals.tf`:

| Setting | Location | Description |
|---------|----------|-------------|
| `project` | `locals.tf` | Project name prefix (`tobrazo`) |
| `env` | `locals.tf` | Environment (`prod`) |
| VPC CIDR | `vpc.tf` | `10.0.0.0/16` |
| Availability Zones | `vpc.tf` | `eu-central-1a/b/c` |
| Cloudflare tokens | `terraform.tfvars` | DNS/cert-manager API tokens |
| ArgoCD hostname | `locals.tf` | `argocd.example.com` |
| App secrets | `terraform.tfvars` | B2B and NestJS backend secrets |

---

## Security Notes

- State backend encrypted with S3 SSE and DynamoDB for locking
- EFS encrypted with customer-managed KMS key
- Worker nodes in private subnets only
- ALB security group restricts inbound to HTTPS
- IRSA provides pod-level IAM without node credentials
- Secrets stored in AWS Secrets Manager, not in Git

---

## Post-Deployment Resources

Terraform also creates Kubernetes resources after cluster provisioning:

- **ClusterIssuer** for Let's Encrypt DNS validation via Cloudflare
- **ArgoCD Root Application** pointing to `gitops/envs/prod` for GitOps bootstrap

---

## Recommendations

- [ ] Enable multi-NAT for production HA
- [ ] Add VPC Flow Logs for network visibility
- [ ] Implement Terraform Cloud for PR-based workflows
- [ ] Restrict `api_allow_cidrs` from `0.0.0.0/0`
- [ ] Add network policies for pod isolation
- [ ] Set up CloudWatch alarms for EKS/EFS metrics
