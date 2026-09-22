"""keyross doctor — is the agent ready for a cluster? v0.1: static checks. Never reads the value of a secret."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SECRET_PATTERNS = {
    "generic API key": re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    "Anthropic key": re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"),
    "OpenAI key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "AWS key": re.compile(r"AKIA[0-9A-Z]{16}"),
}


@dataclass
class Finding:
    check: str
    ok: bool
    detail: str
    where: str = ""
    fix: str = ""


def check_secrets_in_repo(root: Path) -> list[Finding]:
    """Detect secrets in the code — report the type and the location, never the value."""
    out = []
    for f in root.rglob("*"):
        if f.is_dir() or f.suffix not in (".py", ".yaml", ".yml", ".toml", ".env", ".json", ".txt", ".md") or ".git" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for name, pat in SECRET_PATTERNS.items():
                if pat.search(line):
                    out.append(Finding("secrets.repo", False, f"probable {name}", f"{f}:{i}", "move it to a Kubernetes Secret / an environment variable"))
    if not out:
        out.append(Finding("secrets.repo", True, "no secret pattern in the repository"))
    return out


def check_env_files(root: Path) -> list[Finding]:
    envs = [str(p) for p in root.rglob(".env*") if p.is_file()]
    return [Finding("secrets.envfile", not envs, "no .env file" if not envs else f"{len(envs)} .env file(s) present", ", ".join(envs),
                    "never ship a .env inside an image; use Secret + ConfigMap")]


def check_dockerfile(root: Path) -> list[Finding]:
    out = []
    for df in root.rglob("*Dockerfile*"):
        text = df.read_text(encoding="utf-8", errors="ignore")
        out.append(Finding("image.nonroot", "USER " in text, "USER set" if "USER " in text else "no USER: container runs as root", str(df), "add a non-root user"))
        out.append(Finding("image.healthcheck", "HEALTHCHECK" in text, "HEALTHCHECK present" if "HEALTHCHECK" in text else "no HEALTHCHECK", str(df), "declare a health endpoint"))
        out.append(Finding("image.pinned", ":latest" not in text, "base image pinned" if ":latest" not in text else "base image uses latest", str(df), "pin the base image version"))
    if not out:
        out.append(Finding("image.dockerfile", False, "no Dockerfile found", "", "the agent must be containerized to run in a cluster"))
    return out


def check_manifests(root: Path) -> list[Finding]:
    out = []
    manifests = list(root.rglob("*.yaml")) + list(root.rglob("*.yml"))
    for m in manifests:
        text = m.read_text(encoding="utf-8", errors="ignore")
        if "kind: Deployment" not in text and "kind: StatefulSet" not in text:
            continue
        out.append(Finding("k8s.limits", "limits:" in text, "resource limits declared" if "limits:" in text else "no resource limits", str(m), "add requests / limits"))
        out.append(Finding("k8s.probes", "livenessProbe" in text or "readinessProbe" in text, "probes present" if "Probe" in text else "no probe", str(m), "add liveness / readiness"))
        out.append(Finding("k8s.no_latest", ":latest" not in text, "images tagged" if ":latest" not in text else "image uses latest", str(m), "tag = commit sha"))
        has_ref = "secretRef" in text or "secretKeyRef" in text
        out.append(Finding("k8s.secretref", has_ref or "value:" not in text, "secrets referenced" if has_ref else "check: literal values in env?", str(m), "use secretRef / configMapRef"))
        out.append(Finding("k8s.nonroot", "runAsNonRoot: true" in text, "runAsNonRoot" if "runAsNonRoot: true" in text else "no runAsNonRoot", str(m), "securityContext.runAsNonRoot: true"))
    has_np = any("kind: NetworkPolicy" in p.read_text(encoding="utf-8", errors="ignore") for p in manifests)
    out.append(Finding("k8s.networkpolicy", has_np, "NetworkPolicy present" if has_np else "no NetworkPolicy", "", "deny-all + explicit worker egress"))
    return out


def run_static(root: str | Path = ".") -> list[Finding]:
    r = Path(root)
    return check_secrets_in_repo(r) + check_env_files(r) + check_dockerfile(r) + check_manifests(r)


def render(findings: list[Finding]) -> str:
    lines = ["keyross doctor (static)"]
    for f in findings:
        mark = "✔" if f.ok else "✘"
        where = f"  ({f.where})" if f.where else ""
        fix = f"  → {f.fix}" if (not f.ok and f.fix) else ""
        lines.append(f"  {mark} {f.check:<20} {f.detail}{where}{fix}")
    bad = sum(1 for f in findings if not f.ok)
    lines.append(f"{len(findings) - bad} green · {bad} to fix — behavioural checks (SIGTERM, idempotence, egress, gate) come with `doctor image:` and `doctor --kind`")
    return "\n".join(lines)
