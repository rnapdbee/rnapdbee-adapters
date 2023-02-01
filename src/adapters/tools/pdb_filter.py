from typing import Callable, Dict, Iterable, Tuple, List

from adapters.tools import maxit
from adapters.exceptions import PdbParsingError


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
        raise PdbParsingError(f'File has {models_count} model(s), number {model} passed.')

    new_content = ''.join(new_content_arr)
    return new_content


def replace_chains(pdb_content: str) -> Tuple[str, Dict[str, str]]:
    chains_symbols = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz!@#$%^&*()-=_+[]{},.<>/?'
    new_chains = iter(chains_symbols)
    new_content: List[str] = []
    mapped_chains: Dict[str, str] = {}

    for line in pdb_content.splitlines(True):
        if any(line.startswith(token) for token in ('ATOM', 'HETATM', 'TER')):
            chain = line[20:22].strip()
            if chain not in mapped_chains:
                try:
                    mapped_chains[chain] = next(new_chains)
                except StopIteration as exc:
                    raise PdbParsingError(f'Maximum number of chains ({len(chains_symbols)}) in PDB exceeded!') from exc
            new_line = f'{line[:20]} {mapped_chains[chain]}{line[22:]}'
            new_content.append(new_line)

    return ''.join(new_content), {value: key for key, value in mapped_chains.items()}
