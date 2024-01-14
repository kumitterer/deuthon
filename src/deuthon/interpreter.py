from .transformer import parse_german_code

def interpreter():
    while True:
        try:
            german_code = input('>>> ')
        except EOFError:
            break

        python_code = parse_german_code(german_code)
        exec(python_code)