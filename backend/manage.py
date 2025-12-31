from app import create_app
from app.db import db
from flask_migrate import Migrate

# PUBLIC_INTERFACE
def main():
    """Flask CLI entrypoint for migrations.

    Usage:
      export FLASK_APP=manage.py
      flask db init
      flask db migrate -m "init"
      flask db upgrade
    """
    _ = create_app()
    Migrate(_, db)


if __name__ == "__main__":
    main()
