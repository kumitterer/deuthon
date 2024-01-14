#!/usr/bin/env python3

import ast
import tokenize
import pathlib
import setuptools
import sys
import traceback

from argparse import ArgumentParser

from deuthon.transformer import parse_german_code, prepare_builtin_overrides
from deuthon.importer import install_deuthon_importer, import_base
from deuthon.interpreter import interpreter

import deuthon.base


def main():
    args = ArgumentParser()
    args.add_argument("file", default="", nargs="?")
    args.add_argument("--version", "-V", action="version", version="Deuthon 0.1.0")
    args = args.parse_args()

    prepare_builtin_overrides()
    install_deuthon_importer(pathlib.Path(__file__).parent / "wrappers")
    import_base(pathlib.Path(__file__).parent / "base")

    if args.file:
        with open(args.file) as f:
            german_code = f.read()

        python_code = parse_german_code(german_code)

        code_object = compile(
            python_code,
            pathlib.Path(args.file).absolute(),
            "exec",
            dont_inherit=True,
            optimize=0,
        )

        try:
            exec(code_object, {"__file__": pathlib.Path(args.file).absolute()})
        except Ausnahme as e:
            # Extract traceback information, excluding frames related to the interpreter
            tb = e.__traceback__
            while tb is not None:
                if __file__ in tb.tb_frame.f_code.co_filename:
                    # Remove this frame from the traceback
                    if tb.tb_next is None:
                        # Reached the end of the traceback linked list; remove reference to this frame
                        tb = None
                    else:
                        # Skip this frame and link the previous frame to the next one
                        tb = tb.tb_next
                else:
                    break

            # Format and print the modified traceback
            formatted_tb = "".join(traceback.format_exception(type(e), e, tb))
            print(formatted_tb, file=sys.stderr, end="")
            return 1

    else:
        interpreter()


if __name__ == "__main__":
    sys.exit(main())
