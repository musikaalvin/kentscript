#!/usr/bin/env python3
"""
KentScript Package Manager (kpm)
Standalone package manager for KentScript
"""

import os
import sys
import json
import datetime
import platform
import argparse
import hashlib
import shutil
from pathlib import Path
from typing import Optional


class KpmError(Exception):
    """Base exception for kpm errors"""

    pass


class PackageNotFoundError(KpmError):
    """Package not found in registry"""

    pass


class PackageAlreadyInstalledError(KpmError):
    """Package already installed"""

    pass


class DependencyError(KpmError):
    """Dependency resolution failed"""

    pass


class KentScriptPackageManager:
    """Real package manager for KentScript (like pip)"""

    DEFAULT_REGISTRY = (
        "https://raw.githubusercontent.com/musikaalvin/kentscript/packages/main"
    )
    VERSION_CONSTRAINTS = {
        "==": lambda v, c: v == c,
        "!=": lambda v, c: v != c,
        ">": lambda v, c: v > c,
        ">=": lambda v, c: v >= c,
        "<": lambda v, c: v < c,
        "<=": lambda v, c: v <= c,
        "~=": lambda v, c: v.startswith(c),
    }

    def __init__(self, registry_url: Optional[str] = None, verbose: bool = False):
        self.registry_url = registry_url or os.environ.get(
            "KPM_REGISTRY", self.DEFAULT_REGISTRY
        )
        self.verbose = verbose
        self.platform = self._get_platform()
        self.install_dir = self._get_install_dir()
        self.cache_dir = self._get_cache_dir()
        self.config_dir = self._get_config_dir()
        self.loaded_modules = {}
        self.config = self._load_config()
        os.makedirs(self.install_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)

    def _log(self, msg: str):
        if self.verbose:
            print(f"[kpm] {msg}", file=sys.stderr)

    def _get_platform(self):
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        return system

    def _get_install_dir(self):
        if self.platform == "windows":
            appdata = os.getenv("APPDATA", os.path.expanduser("~"))
            return os.path.join(appdata, "ks_packages")
        return os.path.expanduser("~/.ks_packages")

    def _get_cache_dir(self):
        if self.platform == "windows":
            appdata = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
            return os.path.join(appdata, "ks_cache")
        return os.path.expanduser("~/.cache/kentscript")

    def _get_config_dir(self):
        if self.platform == "windows":
            appdata = os.getenv("APPDATA", os.path.expanduser("~"))
            return os.path.join(appdata, "kpm")
        return os.path.expanduser("~/.config/kpm")

    def _load_config(self) -> dict:
        config_path = os.path.join(self.config_dir, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
        return {" registries": [self.registry_url], "trusted_registries": []}

    def _save_config(self):
        config_path = os.path.join(self.config_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def _fetch_url(self, url: str) -> str:
        try:
            import urllib.request
            import urllib.error

            self._log(f"Fetching {url}")
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise PackageNotFoundError(f"Resource not found: {url}")
            raise KpmError(f"HTTP {e.code}: {url}")
        except Exception as e:
            raise KpmError(f"Failed to fetch {url}: {e}")

    def _parse_version(self, version: str) -> tuple:
        parts = version.split(".")
        return tuple(int(p) for p in parts if p.isdigit())

    def _check_version_constraint(self, version: str, constraint: str) -> bool:
        for op, check in self.VERSION_CONSTRAINTS.items():
            if constraint.startswith(op):
                target = constraint[len(op) :]
                if op == "~=":
                    return check(version, target)
                try:
                    return check(
                        self._parse_version(version), self._parse_version(target)
                    )
                except ValueError:
                    return False
        return True

    def _get_package_index(self, registry: Optional[str] = None) -> dict:
        reg = registry or self.registry_url
        index_url = f"{reg}/index.json"
        cache_file = os.path.join(
            self.cache_dir, f"index_{hashlib.md5(reg.encode()).hexdigest()}.json"
        )

        try:
            content = self._fetch_url(index_url)
            index = json.loads(content)
            with open(cache_file, "w") as f:
                f.write(content)
            return index
        except KpmError:
            if os.path.exists(cache_file):
                self._log(f"Using cached index from {cache_file}")
                with open(cache_file, "r") as f:
                    return json.load(f)
            raise

    def resolve_version(
        self, package_name: str, version_constraint: Optional[str] = None
    ) -> str:
        index = self._get_package_index()
        if package_name not in index:
            raise PackageNotFoundError(
                f"Package '{package_name}' not found in registry"
            )

        pkg_info = index[package_name]
        versions = pkg_info.get("versions", [])
        latest = pkg_info.get("latest", "1.0.0")

        if not version_constraint:
            return latest

        if not versions:
            return latest

        for v in reversed(versions):
            if self._check_version_constraint(v, version_constraint):
                return v

        raise KpmError(f"No version matching '{version_constraint}' for {package_name}")

    def install(
        self,
        package_name: str,
        version: Optional[str] = None,
        no_deps: bool = False,
        force: bool = False,
        registry: Optional[str] = None,
    ):
        """Install package from registry"""
        pkg_path = os.path.join(self.install_dir, f"{package_name}.ks")

        if os.path.exists(pkg_path) and not force:
            raise PackageAlreadyInstalledError(
                f"Package '{package_name}' already installed. Use --force to reinstall."
            )

        resolved_version = self.resolve_version(package_name, version)
        self._log(f"Resolved {package_name}@{resolved_version}")

        index = self._get_package_index(registry)
        pkg_info = index.get(package_name, {})

        if not no_deps and "dependencies" in pkg_info:
            self._install_dependencies(pkg_info["dependencies"], registry)

        reg = registry or self.registry_url
        package_urls = [
            f"{reg}/{package_name}/{resolved_version}/{package_name}.ks",
            f"{reg}/{package_name}/{resolved_version}.ks",
            f"{reg}/{package_name}.ks",
        ]

        content = None
        for url in package_urls:
            try:
                content = self._fetch_url(url)
                break
            except KpmError:
                continue

        if content is None:
            raise PackageNotFoundError(f"Could not download {package_name}")

        checksum = hashlib.sha256(content.encode()).hexdigest()

        with open(pkg_path, "w") as f:
            f.write(content)

        metadata = {
            "name": package_name,
            "version": resolved_version,
            "installed": datetime.datetime.now().isoformat(),
            "registry": reg,
            "checksum": checksum,
            "dependencies": pkg_info.get("dependencies", []),
        }
        meta_path = os.path.join(self.install_dir, f"{package_name}.meta.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"✓ Installed {package_name} {resolved_version}")
        return pkg_path

    def _install_dependencies(self, dependencies: dict, registry: Optional[str]):
        for dep_name, constraint in dependencies.items():
            dep_path = os.path.join(self.install_dir, f"{dep_name}.ks")
            if not os.path.exists(dep_path):
                self._log(f"Installing dependency: {dep_name}{constraint}")
                try:
                    self.install(dep_name, constraint, no_deps=True, registry=registry)
                except KpmError as e:
                    raise DependencyError(f"Failed to install {dep_name}: {e}")

    def uninstall(self, package_name: str, no_deps: bool = False):
        """Uninstall package"""
        pkg_path = os.path.join(self.install_dir, f"{package_name}.ks")
        meta_path = os.path.join(self.install_dir, f"{package_name}.meta.json")

        if not os.path.exists(pkg_path):
            raise PackageNotFoundError(f"Package '{package_name}' not installed")

        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)

        dependents = self._find_dependents(package_name)
        if dependents and not no_deps:
            raise DependencyError(
                f"Cannot uninstall {package_name}: required by {', '.join(dependents)}"
            )

        os.remove(pkg_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)

        print(f"✓ Uninstalled {package_name}")

    def _find_dependents(self, package_name: str) -> list:
        dependents = []
        for file in os.listdir(self.install_dir):
            if file.endswith(".meta.json"):
                with open(os.path.join(self.install_dir, file), "r") as f:
                    meta = json.load(f)
                    deps = meta.get("dependencies", {})
                    if package_name in deps:
                        dependents.append(meta["name"])
        return dependents

    def update(self, package_name: str = None):
        """Update package(s)"""
        if package_name:
            self._update_single(package_name)
        else:
            for pkg in self.list_installed():
                self._update_single(pkg["name"])

    def _update_single(self, package_name: str):
        meta_path = os.path.join(self.install_dir, f"{package_name}.meta.json")
        if not os.path.exists(meta_path):
            raise PackageNotFoundError(f"Package '{package_name}' not installed")

        with open(meta_path, "r") as f:
            meta = json.load(f)

        current_version = meta["version"]
        latest_version = self.resolve_version(package_name)

        if self._parse_version(current_version) >= self._parse_version(latest_version):
            print(f"{package_name} is up-to-date ({current_version})")
            return

        print(f"Updating {package_name} {current_version} -> {latest_version}")
        self.install(package_name, force=True, registry=meta.get("registry"))

    def list_installed(self) -> list:
        """List installed packages"""
        packages = []
        for file in os.listdir(self.install_dir):
            if file.endswith(".meta.json"):
                with open(os.path.join(self.install_dir, file), "r") as f:
                    packages.append(json.load(f))
        return sorted(packages, key=lambda x: x["name"])

    def search(self, query: str, registry: Optional[str] = None) -> list:
        """Search packages in registry"""
        index = self._get_package_index(registry)
        results = []
        query_lower = query.lower()
        for name, info in index.items():
            if (
                query_lower in name.lower()
                or query_lower in info.get("description", "").lower()
            ):
                results.append({"name": name, **info})
        return sorted(results, key=lambda x: x.get("stars", 0), reverse=True)

    def info(self, package_name: str) -> dict:
        """Get package info"""
        meta_path = os.path.join(self.install_dir, f"{package_name}.meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                return json.load(f)

        index = self._get_package_index()
        if package_name not in index:
            raise PackageNotFoundError(f"Package '{package_name}' not found")
        return index[package_name]

    def link(self, source_path: str, package_name: str = None):
        """Link local package for development"""
        source = Path(source_path).resolve()
        if not source.exists():
            raise KpmError(f"Source path does not exist: {source}")

        if package_name is None:
            package_name = source.stem

        link_path = os.path.join(self.install_dir, f"{package_name}.ks")
        meta_path = os.path.join(self.install_dir, f"{package_name}.meta.json")

        if os.path.isfile(source):
            shutil.copy(source, link_path)
        else:
            ks_file = source / f"{package_name}.ks"
            if ks_file.exists():
                shutil.copy(ks_file, link_path)
            else:
                raise KpmError(f"No {package_name}.ks found in {source}")

        metadata = {
            "name": package_name,
            "version": "0.0.0-dev",
            "installed": datetime.datetime.now().isoformat(),
            "linked": str(source),
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"✓ Linked {package_name} -> {source}")

    def unlink(self, package_name: str):
        """Unlink local package"""
        meta_path = os.path.join(self.install_dir, f"{package_name}.meta.json")
        if not os.path.exists(meta_path):
            raise PackageNotFoundError(f"Package '{package_name}' not installed")

        with open(meta_path, "r") as f:
            meta = json.load(f)

        if "linked" not in meta:
            raise KpmError(f"Package '{package_name}' is not a linked package")

        pkg_path = os.path.join(self.install_dir, f"{package_name}.ks")
        os.remove(pkg_path)
        os.remove(meta_path)

        print(f"✓ Unlinked {package_name}")

    def find_module(self, module_name: str) -> Optional[str]:
        """Find module file"""
        pkg_path = os.path.join(self.install_dir, f"{module_name}.ks")
        if os.path.exists(pkg_path):
            return pkg_path

        cwd_path = os.path.join(os.getcwd(), f"{module_name}.ks")
        if os.path.exists(cwd_path):
            return cwd_path

        return None

    def load_module(self, module_name: str) -> str:
        """Load module by name"""
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]

        module_path = self.find_module(module_name)
        if not module_path:
            raise ImportError(
                f"Module '{module_name}' not found. Try: kpm install {module_name}"
            )

        with open(module_path, "r") as f:
            module_code = f.read()
        self.loaded_modules[module_name] = module_code
        return module_code


def main():
    parser = argparse.ArgumentParser(
        prog="kpm", description="KentScript Package Manager"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install a package")
    install_parser.add_argument("package", help="Package name[@version]")
    install_parser.add_argument(
        "--no-deps", action="store_true", help="Don't install dependencies"
    )
    install_parser.add_argument(
        "--force", "-f", action="store_true", help="Force reinstall"
    )
    install_parser.add_argument("--registry", "-r", help="Custom registry URL")

    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall a package")
    uninstall_parser.add_argument("package", help="Package name")
    uninstall_parser.add_argument(
        "--no-deps", action="store_true", help="Don't check dependencies"
    )

    update_parser = subparsers.add_parser("update", help="Update package(s)")
    update_parser.add_argument("package", nargs="?", help="Package name (default: all)")

    search_parser = subparsers.add_parser("search", help="Search packages")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--registry", "-r", help="Custom registry URL")

    subparsers.add_parser("list", help="List installed packages")
    subparsers.add_parser("cache-clean", help="Clean cache")

    info_parser = subparsers.add_parser("info", help="Show package info")
    info_parser.add_argument("package", help="Package name")

    link_parser = subparsers.add_parser(
        "link", help="Link local package for development"
    )
    link_parser.add_argument("path", help="Path to package directory or file")
    link_parser.add_argument("name", nargs="?", help="Package name")

    unlink_parser = subparsers.add_parser("unlink", help="Unlink local package")
    unlink_parser.add_argument("package", help="Package name")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--version", action="version", version="kpm 1.0.0")

    args = parser.parse_args()

    try:
        kpm = KentScriptPackageManager(verbose=args.verbose)

        if args.command == "install":
            pkg_spec = args.package
            version = None
            if "@" in pkg_spec:
                pkg_name, version = pkg_spec.split("@", 1)
            else:
                pkg_name = pkg_spec
            kpm.install(
                pkg_name,
                version,
                no_deps=args.no_deps,
                force=args.force,
                registry=args.registry,
            )

        elif args.command == "uninstall":
            kpm.uninstall(args.package, no_deps=args.no_deps)

        elif args.command == "update":
            kpm.update(args.package)

        elif args.command == "search":
            results = kpm.search(args.query, registry=args.registry)
            if results:
                for pkg in results:
                    print(
                        f"{pkg['name']} {pkg.get('latest', '?')} - {pkg.get('description', '')}"
                    )
            else:
                print("No packages found")

        elif args.command == "list":
            packages = kpm.list_installed()
            if packages:
                print("Installed packages:")
                for pkg in packages:
                    print(f"  {pkg['name']} {pkg['version']}")
            else:
                print("No packages installed")

        elif args.command == "cache-clean":
            if os.path.exists(kpm.cache_dir):
                shutil.rmtree(kpm.cache_dir)
                os.makedirs(kpm.cache_dir)
            print("Cache cleaned")

        elif args.command == "info":
            info = kpm.info(args.package)
            print(json.dumps(info, indent=2))

        elif args.command == "link":
            kpm.link(args.path, args.name)

        elif args.command == "unlink":
            kpm.unlink(args.package)

    except KpmError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
