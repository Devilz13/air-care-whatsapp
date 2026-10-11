"""Local-only operator tasks. No public administrative API."""
import argparse
import getpass
import os
from .core import Store


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("AIRCARE_DB", "data/aircare.db"))
    sub = parser.add_subparsers(dest="action", required=True)
    home = sub.add_parser("add-home")
    home.add_argument("code")
    home.add_argument("name")
    user = sub.add_parser("add-user")
    user.add_argument("phone")
    user.add_argument("homes", nargs="+")
    user.add_argument("--timezone", default="Asia/Singapore")
    remove = sub.add_parser("remove-user")
    remove.add_argument("phone")
    sub.add_parser("delivery-summary")
    args = parser.parse_args()
    store = Store(args.db)
    if args.action == "add-home":
        store.add_home(args.code, args.name, getpass.getpass("Home token (32+ characters): "))
    elif args.action == "add-user":
        store.add_user(args.phone, args.homes, args.timezone)
    elif args.action == "remove-user":
        with store.lock, store.db:
            store.db.execute("DELETE FROM users WHERE phone=?", (args.phone,))
    else:
        for row in store.db.execute("SELECT state,count(*) FROM outbox GROUP BY state"):
            print(row[0], row[1])


if __name__ == "__main__":
    main()
