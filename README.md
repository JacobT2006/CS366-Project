# CS366 Project

A work in progress for the University of Wisconsin–Whitewater CS366 course. The repository is intended to become a Python application backed by MariaDB, but the application itself has not been implemented yet.

## Project files

- `frontEnd.py` — frontend placeholder; no interface is implemented yet.
- `backEnd.py` — backend placeholder; no database operations are implemented yet.
- `runScript.sh` — checks the required command line tools and then runs `updateProject.sh`.
- `updateProject.sh` — sets the Git `origin` remote to this project’s GitHub URL and pulls the current branch using fast-forward only.
- `LICENSE` — MIT License.

## Requirements

The launcher currently requires:

- Python 3.15.0 or newer (`python3`)
- MariaDB command line client (`mariadb`)
- Git

The Python and MariaDB checks are performed by `runScript.sh`. Git is needed by the update script. The launcher does not install any of these tools or configure a MariaDB server/database.

## Run the launcher

From the project directory, run:

```bash
chmod u+x runScript.sh
./runScript.sh
```

The launcher checks Python and MariaDB versions/availability, makes `updateProject.sh` executable, and runs it. The update script changes the repository’s `origin` URL to `https://github.com/JacobT2006/CS366-Project.git`, then pulls the current branch with `--ff-only`. Run it from a Git checkout with a named branch and a working network connection. If the local branch cannot be fast-forwarded, Git stops the update.

After syncing, the launcher currently has no application command to run. The frontend and backend need implementation before this repository can be used as a database application.

## Development setup

Create and activate a virtual environment if you plan to add Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies as they are added to the project. There is not currently a dependency manifest or a configured database schema.

## License

This project is distributed under the MIT License. See [`LICENSE`](LICENSE).
