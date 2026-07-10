import os
import re
import json
from typing import Optional


class DependencyParser:
    def parse_dependencies(self, project_dir: str) -> dict:
        result = {
            "languages": [],
            "dependencies": [],
            "build_tools": [],
            "cves": [],
        }

        for root, dirs, files in os.walk(project_dir):
            for f in files:
                filepath = os.path.join(root, f)
                if f == "pom.xml":
                    result["languages"].append("Java")
                    result["build_tools"].append("Maven")
                    deps = self._parse_pom_xml(filepath)
                    result["dependencies"].extend(deps)

                elif f == "build.gradle" or f == "build.gradle.kts":
                    result["languages"].append("Java")
                    result["build_tools"].append("Gradle")
                    deps = self._parse_gradle(filepath)
                    result["dependencies"].extend(deps)

                elif f == "package.json":
                    result["languages"].append("JavaScript/TypeScript")
                    result["build_tools"].append("npm/yarn")
                    deps = self._parse_package_json(filepath)
                    result["dependencies"].extend(deps)

                elif f == "requirements.txt":
                    result["languages"].append("Python")
                    result["build_tools"].append("pip")
                    deps = self._parse_requirements_txt(filepath)
                    result["dependencies"].extend(deps)

                elif f == "composer.json":
                    result["languages"].append("PHP")
                    result["build_tools"].append("Composer")
                    deps = self._parse_composer_json(filepath)
                    result["dependencies"].extend(deps)

                elif f == "go.mod":
                    result["languages"].append("Go")
                    result["build_tools"].append("Go Modules")
                    deps = self._parse_go_mod(filepath)
                    result["dependencies"].extend(deps)

                elif f.endswith(".csproj"):
                    result["languages"].append("C#/.NET")
                    result["build_tools"].append("NuGet")
                    deps = self._parse_csproj(filepath)
                    result["dependencies"].extend(deps)

        result["languages"] = list(set(result["languages"]))
        result["build_tools"] = list(set(result["build_tools"]))
        return result

    def _parse_pom_xml(self, filepath: str) -> list:
        deps = []
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(filepath)
            root = tree.getroot()
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}
            for dep in root.findall(".//m:dependency", ns):
                group = dep.find("m:groupId", ns)
                artifact = dep.find("m:artifactId", ns)
                version = dep.find("m:version", ns)
                if group is not None and artifact is not None:
                    deps.append({
                        "name": f"{group.text}:{artifact.text}",
                        "version": version.text if version is not None else "unknown",
                        "type": "maven",
                        "file": filepath,
                    })
        except Exception:
            pass
        return deps

    def _parse_gradle(self, filepath: str) -> list:
        deps = []
        try:
            with open(filepath, "r") as f:
                content = f.read()
            for match in re.finditer(r"(implementation|api|compile)\s+['\"]([^:]+):([^:]+):([^'\"]+)['\"]", content):
                deps.append({
                    "name": f"{match.group(2)}:{match.group(3)}",
                    "version": match.group(4),
                    "type": "gradle",
                    "file": filepath,
                })
        except Exception:
            pass
        return deps

    def _parse_package_json(self, filepath: str) -> list:
        deps = []
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            for dep_type in ["dependencies", "devDependencies"]:
                for name, version in data.get(dep_type, {}).items():
                    deps.append({
                        "name": name,
                        "version": version,
                        "type": "npm",
                        "file": filepath,
                    })
        except Exception:
            pass
        return deps

    def _parse_requirements_txt(self, filepath: str) -> list:
        deps = []
        try:
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        parts = re.split(r"[=~<>!]+", line)
                        if parts:
                            deps.append({
                                "name": parts[0].strip(),
                                "version": parts[1].strip() if len(parts) > 1 else "latest",
                                "type": "pip",
                                "file": filepath,
                            })
        except Exception:
            pass
        return deps

    def _parse_composer_json(self, filepath: str) -> list:
        deps = []
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            for dep_type in ["require", "require-dev"]:
                for name, version in data.get(dep_type, {}).items():
                    deps.append({
                        "name": name,
                        "version": version,
                        "type": "composer",
                        "file": filepath,
                    })
        except Exception:
            pass
        return deps

    def _parse_go_mod(self, filepath: str) -> list:
        deps = []
        try:
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("go ") and not line.startswith("module "):
                        parts = line.split()
                        if len(parts) >= 2 and not line.startswith("require"):
                            deps.append({
                                "name": parts[0],
                                "version": parts[1] if len(parts) > 1 else "unknown",
                                "type": "go",
                                "file": filepath,
                            })
        except Exception:
            pass
        return deps

    def _parse_csproj(self, filepath: str) -> list:
        deps = []
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(filepath)
            root = tree.getroot()
            ns = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}
            for ref in root.findall(".//m:PackageReference", ns):
                name = ref.get("Include")
                version = ref.get("Version")
                if name:
                    deps.append({
                        "name": name,
                        "version": version or "unknown",
                        "type": "nuget",
                        "file": filepath,
                    })
        except Exception:
            pass
        return deps
