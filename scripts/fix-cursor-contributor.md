# Fix Cursor Showing as Contributor

GitHub shows Cursor (cursoragent) as a contributor because some commits had `Co-authored-by: Cursor <cursoragent@cursor.com>` in the commit message. This guide removes that.

## Step 1: Verify Your Local Main Is Clean

Your **current** local main should already be clean (commit `a13d11a` has only slappepolsen, no Co-authored-by). Verify:

```bash
cd /Users/kszxvd/Documents/sp-workshop-github
git log main -1 --format="%B" | grep -i cursor
```

If that prints **nothing**, your latest commit is clean. If it prints "Co-authored-by: Cursor", continue to Step 4.

## Step 2: Force Push to Replace GitHub History

Replace GitHub's history with your clean local history:

```bash
cd /Users/kszxvd/Documents/sp-workshop-github
git push origin main --force
git push origin v9.2.2 --force
```

## Step 3: Refresh GitHub's Contributor Cache (if Cursor still appears)

GitHub caches contributors. If Cursor still shows after force push:

1. Go to **https://github.com/slappepolsen/sp-workshop/settings/branches**
2. Change default branch from `main` to `main2` (create a temp branch first if needed), save
3. Change it back to `main`, save
4. Wait a few hours for the contributor list to refresh

## Step 4: Prevent Future Co-authored-by

Run the install script (or manually copy the hook):

```bash
cd /path/to/sp-workshop
./scripts/install-hooks.sh
```

Or manually:
```bash
cp scripts/prepare-commit-msg .git/hooks/
chmod +x .git/hooks/prepare-commit-msg
```

**Important:** Do this in any clone you use. The hook strips `Co-authored-by: Cursor` before each commit.

## Commits That Had Co-authored-by (orphaned, not in main history)

These were found in reflog/orphaned; they are **not** in the current main branch:

| Commit   | Status                                  |
|----------|-----------------------------------------|
| 05d0a25  | Orphaned – was pushed to GitHub         |
| bb6c9f4  | Orphaned – amend                        |
| 0fe36a1  | Orphaned – filter-branch                |
| 92769c5  | Orphaned – amend                        |

**Current main tip:** `a13d11a` – clean, only slappepolsen.
