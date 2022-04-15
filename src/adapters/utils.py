def is_cif(file_content: str) -> bool:
    for line in file_content.splitlines():
        if line.startswith('_atom_site'):
            return True
    return False
