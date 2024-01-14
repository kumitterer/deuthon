import importlib.abc
import importlib.util
import importlib.machinery
import os
import tokenize
import pathlib
import sys
import builtins

from .transformer import parse_german_code


class DeuthonSourceLoader(importlib.machinery.SourceFileLoader):
    def create_module(self, spec):
        # Creating the module instance. The import system will then call exec_module.
        module = super().create_module(spec)
        if module is not None:
            # Set __package__ if not already set
            if module.__package__ is None:
                module.__package__ = (
                    spec.name
                    if spec.submodule_search_locations is None
                    else spec.parent
                )
        return module

    def exec_module(self, module):
        # The module's __file__ attribute must be set prior to the code execution to support relative imports.
        module.__file__ = self.get_filename(module.__name__)
        # Call the parent method to execute the module body
        super().exec_module(module)

    def source_to_code(self, data, path, *, _optimize=-1):
        reader = tokenize.open(path)
        try:
            encoding = reader.encoding
            source_data = reader.read()
        finally:
            reader.close()

        transpiled_code = parse_german_code(source_data)
        return compile(
            transpiled_code, path, "exec", dont_inherit=True, optimize=_optimize
        )


class DeuthonModuleFinder(importlib.abc.MetaPathFinder):
    def __init__(self, wrappers_directory, extension=".deu"):
        self.wrappers_directory = wrappers_directory
        self.extension = extension

    def find_spec(self, fullname, path, target=None):
        # Check inside the wrappers directory first
        deu_wrapper_path = os.path.join(
            self.wrappers_directory, fullname + self.extension
        )
        if os.path.isfile(deu_wrapper_path):
            loader = DeuthonSourceLoader(fullname, deu_wrapper_path)
            spec = importlib.util.spec_from_loader(
                fullname, loader, origin=deu_wrapper_path
            )
            return spec

        # Check for a .py wrapper
        wrapper_path = os.path.join(self.wrappers_directory, fullname + ".py")
        if os.path.isfile(wrapper_path):
            return importlib.util.spec_from_file_location(fullname, wrapper_path)

        # Check for a wrapper package
        deu_wrapper_path = self._find_deu_file(fullname, [self.wrappers_directory])
        if deu_wrapper_path:
            loader = DeuthonSourceLoader(fullname, deu_wrapper_path)
            spec = importlib.util.spec_from_loader(
                fullname, loader, origin=deu_wrapper_path
            )
            return spec

        # If it's not a wrapper, look for a .deu file
        deu_path = self._find_deu_file(fullname, path)
        if deu_path:
            loader = DeuthonSourceLoader(fullname, deu_path)
            spec = importlib.util.spec_from_loader(fullname, loader, origin=deu_path)
            if self._is_package(deu_path):
                spec.submodule_search_locations = [os.path.dirname(deu_path)]
            return spec

        # Neither .deu file nor wrapper found
        return None

    def _is_package(self, path):
        # Determine if the path is a package by checking for an __init__.deu file
        return os.path.isdir(path) and os.path.isfile(
            os.path.join(path, "__init__.deu")
        )

    def _find_deu_file(self, fullname, path=None):
        # Determine search paths
        if not path:
            # If 'path' is not provided, create a search path
            # Including the current directory and any DEUTHON_PATH directories
            path = ["."]
            deuthon_path = os.environ.get("DEUTHON_PATH")
            if deuthon_path:
                path.extend(deuthon_path.split(os.pathsep))

        # The base name for the file we're trying to find will be the last component of 'fullname'
        # e.g., for 'testmodul.submodul.test', we want to end up with 'test.deu'
        module_basename = (
            fullname.rpartition(".")[-1] + self.extension
        )  # e.g., 'test.deu'

        for entry in path:
            module_full_path = os.path.join(
                entry, fullname.replace(".", "/") + self.extension
            )
            init_full_path = os.path.join(
                entry, fullname.replace(".", "/"), "__init__" + self.extension
            )

            if os.path.isfile(
                module_full_path
            ):  # Regular module (or top-level package)
                return module_full_path

            if os.path.isdir(os.path.dirname(init_full_path)) and os.path.isfile(
                init_full_path
            ):  # Package
                return init_full_path

        return None  # No module or package found


def install_deuthon_importer(wrappers_directory):
    deuthon_finder = DeuthonModuleFinder(wrappers_directory)
    sys.meta_path.insert(0, deuthon_finder)


def import_base(base_directory):
    # Find all .deu files in the given directory
    for filename in os.listdir(base_directory):
        if filename.endswith(".deu"):
            # Construct module name from file name
            module_name = filename[:-4]  # Remove .deu extension
            module_path = os.path.join(base_directory, filename)

            # Load the module using DeuthonSourceLoader
            loader = DeuthonSourceLoader(module_name, module_path)
            spec = importlib.util.spec_from_loader(
                module_name, loader, origin=module_path
            )
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)

            # Add all names that don't start with an underscore to builtins
            for name in dir(module):
                if not name.startswith("_"):
                    setattr(builtins, name, getattr(module, name))
