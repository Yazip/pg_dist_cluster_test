import pathlib
import subprocess

def create_diffs(result_file: pathlib.Path, expected_file: pathlib.Path, diff_file: pathlib.Path) -> bool:
    """Compare a result file with the expected output and write a diff if they differ.

    Uses the 'diff -u' Unix command to generate unified diffs.

    Args:
        result_file (Path): Path to the generated output file.
        expected_file (Path): Path to the expected output file.
        diff_file (Path): Path to write the diff if differences are found.

    Returns:
        bool: True if files match exactly, False otherwise.
    """
    proc = subprocess.run(
        ["diff", "-u", expected_file, result_file],
        stdout=subprocess.PIPE,
        text=True,
    )

    if proc.returncode == 0:
        return True

    diff_file.write_text(proc.stdout)
    return False