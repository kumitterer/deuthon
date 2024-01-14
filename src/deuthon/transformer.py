import ast
import tokenize

from io import BytesIO

from .dictionary import dictionary

def translate_german_keywords(tokens):
    for token in tokens:
        # Translate German keywords to English
        if token.type == tokenize.NAME and token.string in dictionary:
            yield token._replace(string=dictionary[token.string])
        else:
            yield token

def parse_german_code(german_code):
    # Convert the German code into bytes for tokenization
    bytes_code = bytes(german_code, 'utf-8')

    # Tokenize the German code
    tokens = tokenize.tokenize(BytesIO(bytes_code).readline)

    # Translate German tokens to their English (Python) counterparts
    english_tokens = translate_german_keywords(tokens)

    # Detokenize back to a code string in English/Python
    python_code_str = tokenize.untokenize(english_tokens).decode('utf-8')

    # Return the compiled Python code object
    return python_code_str

def prepare_builtin_overrides():
    import sys

    original_json = sys.modules["json"]
    sys.modules["sysjson"] = original_json
    del sys.modules["json"]