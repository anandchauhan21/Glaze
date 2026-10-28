"""Print locally; never post this URL or include it in screenshots."""
import secrets, os, argparse
from .config import ROOT

def main():
    p=argparse.ArgumentParser();p.add_argument('--rotate',action='store_true');args=p.parse_args()
    token=ROOT/'dashboard/access-token'
    if token.is_symlink():raise SystemExit('Refusing symlink token file')
    if args.rotate:
        os.umask(0o077);token.parent.mkdir(parents=True,exist_ok=True)
        token.write_text(secrets.token_urlsafe(32));token.chmod(0o600)
        print('Token rotated. Restart Glaze before using the new URL.')
    if not token.exists():raise SystemExit('Start Glaze once to create its token.')
    print('http://127.0.0.1:18765/'+token.read_text().strip())
if __name__=='__main__':main()
