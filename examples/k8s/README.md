# Keyross on Kubernetes — planned

Not built, and no date. The idea: run the gate as a Job next to an agent in a cluster, on the documents it wrote, before they leave the namespace.

Today the gate runs wherever Python runs: `keyross gate <folder>` in any container, or in CI with the [GitHub Action](../../integrations/github-action/README.md).
