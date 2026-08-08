<div align="center">

# 🏗️ Terraform

**Infrastructure as Code — cloud provisioning templates.**

![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?style=flat-square&logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-EC2%20%C2%B7%20ELB-FF9900?style=flat-square&logo=amazonwebservices&logoColor=white)

</div>

---

The **IaC** tree of the repo. Each subfolder is a standalone Terraform module you can `init` / `plan` / `apply` on its own.

---

## 📂 Modules

| Module | What it provisions |
|--------|--------------------|
| 🖥️ **[web-server](web-server)** | Two `t2.micro` nginx EC2 instances across two AZs, fronted by a Classic ELB with health checks — on **AWS** (`us-east-1`). Bootstrapped via `user_data`. |

Each module has its own README with an architecture diagram, a configuration reference, and usage steps.

> [!NOTE]
> These modules are learning/reference templates. They hardcode region and sizing for clarity — review and parameterize (and supply your own AWS credentials) before using them anywhere real.
