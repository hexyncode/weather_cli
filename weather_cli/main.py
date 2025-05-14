from .cli import run_cli
from .db import init_db

def main():
    init_db()
    run_cli()

if __name__ == "__main__":
    main()