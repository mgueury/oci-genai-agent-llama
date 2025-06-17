# OCI Infrastructure Setup with Terraform

This terraform configuration creates various OCI resources including VCN, Compute instances, ATP database, API Gateway, and Gen AI resources.

## Prerequisites

1. Install Terraform (version >= 1.0.0)
2. Configure OCI CLI and obtain required credentials
3. Generate SSH key pair for compute instance access

## Configuration

### Required Variables

Create a `terraform.tfvars` file in the terraform directory with the following variables:

```hcl
# Required OCI Provider Configuration
tenancy_ocid         = "<your-tenancy-ocid>"
region               = "<your-region>"              # e.g., us-chicago-1
compartment_ocid     = "<your-compartment-ocid>"

# SSH Keys for Compute Instance
ssh_public_key       = "<path-to-public-key>"      # e.g., ~/.ssh/id_rsa.pub
ssh_private_key      = "<path-to-private-key>"     # e.g., ~/.ssh/id_rsa

# Database Configuration
db_user             = "ADMIN"                     # Default admin user
db_password         = "<your-secure-password>"    # Must be at least 12 characters

# Object Storage Configuration
namespace           = "<your-namespace>"          # Your tenancy's namespace

# Optional Landing Zone Compartments
# If not specified, all resources will be created in the main compartment
lz_web_cmp_ocid     = ""  # Web tier compartment
lz_app_cmp_ocid     = ""  # App tier compartment
lz_db_cmp_ocid      = ""  # Database tier compartment
lz_serv_cmp_ocid    = ""  # Service compartment
lz_network_cmp_ocid = ""  # Network compartment
```

### Optional Variables

You can customize the following variables in `terraform.tfvars`:

```hcl
# Resource Naming
prefix              = "starter"                   # Prefix for all resource names

# Compute Instance Configuration
instance_shape      = "VM.Standard.E5.Flex"      # Shape name
instance_ocpus      = 1                          # Number of OCPUs
instance_shape_config_memory_in_gbs = 8          # Memory in GB

# Database License
license_model       = "BRING_YOUR_OWN_LICENSE"   # or LICENSE_INCLUDED
```

## Usage

1. Initialize Terraform:
```bash
terraform init
```

2. Review the execution plan:
```bash
terraform plan
```

3. Apply the configuration:
```bash
terraform apply
```

4. To destroy the infrastructure:
```bash
terraform destroy
```

## Resource Overview

This configuration creates:
- Virtual Cloud Network (VCN) with public and private subnets
- Compute instance in the public subnet
- Autonomous Database (ATP)
- API Gateway
- Gen AI resources (Agent, Knowledge Base, Data Source)
- Object Storage bucket
- Database Tools connection

## Important Notes

1. The ATP database will be created with version 23ai
2. The compute instance uses Oracle Linux 8
3. All resources will be tagged with the specified prefix
4. Network security lists are configured for common ports (80, 443, 8000, 8080)
5. The configuration uses local backend for state storage