import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from team_repo import team_commit


class TeamRepositoryTest(unittest.TestCase):
    def test_reads_commit_from_the_requested_repository(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
            (root / "tracked.txt").write_text("test\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "test"], check=True)
            expected = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                text=True,
            ).strip()

            self.assertEqual(team_commit(root), expected)

    def test_returns_none_for_a_non_repository(self):
        with TemporaryDirectory() as directory:
            self.assertIsNone(team_commit(directory))


if __name__ == "__main__":
    unittest.main()
