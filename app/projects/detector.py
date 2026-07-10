import os


EXTENSION_MAP = {
    ".java": "Java",
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".cs": "C#",
    ".vb": "VB.NET",
    ".fs": "F#",
    ".php": "PHP",
    ".go": "Go",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".less": "Less",
    ".sql": "SQL",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".json": "JSON",
    ".tf": "Terraform",
    ".dockerfile": "Docker",
    "Dockerfile": "Docker",
}

FRAMEWORK_INDICATORS = {
    "pom.xml": ("Java", "Spring Boot / Maven"),
    "build.gradle": ("Java", "Spring Boot / Gradle"),
    "package.json": ("JavaScript", None),
    "requirements.txt": ("Python", None),
    "Pipfile": ("Python", "Pipenv"),
    "composer.json": ("PHP", "Laravel / Symfony"),
    "go.mod": ("Go", "Go Modules"),
    "*.csproj": ("C#", ".NET Core"),
    "angular.json": ("TypeScript", "Angular"),
    "angular.js": ("JavaScript", "AngularJS"),
    "next.config.js": ("JavaScript", "Next.js"),
    "nuxt.config.js": ("JavaScript", "Nuxt.js"),
    "vue.config.js": ("JavaScript", "Vue.js"),
    "vite.config.ts": ("TypeScript", "Vite"),
}


class LanguageDetector:
    def detect_language(self, filename: str) -> str:
        basename = os.path.basename(filename)
        if basename == "Dockerfile" or basename.startswith("Dockerfile."):
            return "Docker"

        ext = os.path.splitext(filename)[1].lower()
        return EXTENSION_MAP.get(ext, "Unknown")

    def detect_framework(self, project_dir: str) -> str:
        for root, dirs, files in os.walk(project_dir):
            for f in files:
                for indicator, (lang, framework) in FRAMEWORK_INDICATORS.items():
                    if indicator.startswith("*."):
                        ext = indicator.replace("*.", ".")
                        if f.endswith(ext):
                            if framework:
                                return framework
                            elif f == "package.json":
                                return self._detect_js_framework(os.path.join(root, f))
                    elif f == indicator:
                        if framework:
                            return framework
                        elif f == "requirements.txt":
                            return self._detect_python_framework(os.path.join(root, f))
                        elif f == "package.json":
                            return self._detect_js_framework(os.path.join(root, f))
        return "Unknown"

    def _detect_js_framework(self, package_json_path: str) -> str:
        try:
            import json
            with open(package_json_path, "r") as f:
                data = json.load(f)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "react" in deps:
                return "React"
            if "@angular/core" in deps:
                return "Angular"
            if "vue" in deps:
                return "Vue.js"
            if "next" in deps or "next.js" in deps:
                return "Next.js"
            if "express" in deps:
                return "Express"
            return "Node.js"
        except Exception:
            return "Node.js"

    def _detect_python_framework(self, req_path: str) -> str:
        try:
            with open(req_path, "r") as f:
                content = f.read().lower()
            if "django" in content:
                return "Django"
            if "flask" in content:
                return "Flask"
            if "fastapi" in content:
                return "FastAPI"
            return "Python"
        except Exception:
            return "Python"

    def detect_project_language(self, files: list) -> str:
        lang_count = {}
        for f in files:
            if f.lenguaje and f.lenguaje != "Unknown":
                lang_count[f.lenguaje] = lang_count.get(f.lenguaje, 0) + 1
        if not lang_count:
            return "Unknown"
        return max(lang_count, key=lang_count.get)
