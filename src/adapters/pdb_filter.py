from typing import Tuple, Iterable, Callable, Dict
from adapters import maxit


def apply(file_content: str, functions_args: Iterable[Tuple[Callable, Dict]]) -> str:
    pdb_content = maxit.ensure_pdb(file_content)

    for function, kwargs in functions_args:
        pdb_content = function(pdb_content, **kwargs)

    return pdb_content


def leave_single_model(file_content: str, **kwargs) -> str:
    model = int(kwargs.get('model', 1))

    append_mode = True
    new_content_arr = []
    models_count = 0

    for line in file_content.splitlines(True):
        if line.startswith('MODEL'):
            current_model = int(line[10:14].strip())
            models_count += 1
            append_mode = (current_model == model)
        elif line.startswith('ENDMDL'):
            append_mode = True
        elif append_mode:
            new_content_arr.append(line)

    # Only one model in original file
    if models_count == 0:
        models_count = 1

    if model > models_count or model < 1:
        raise ValueError(f'File has {models_count} model(s), number {model} passed.')

    new_content = ''.join(new_content_arr)
    return new_content
