# GEARUP-PD Website

This folder contains the static-site generator for the GEARUP-PD project website.

## Source content

- `GEARUP-PD-BLOG/GEARUP-PD.md` → landing page source
- `GEARUP-PD-BLOG/Blog/*.md` → blog posts
- `GEARUP-PD-BLOG/Resources.md` → resources page

## Build

```bash
cd Website
./build.sh
```

or

```bash
python3 build_site.py
```

or

```bash
npm run build
```

## Output

Generated files are written to:

- `Website/dist/index.html`
- `Website/dist/blog/*.html`
- `Website/dist/assets/styles.css`

## Blog post ordering

Blog posts are ordered automatically by the filesystem creation time of each markdown file, newest first.

## Notes

- The landing page also includes project details distilled from the protocol/recruitment documents found elsewhere in the study folder.
- The “Project Updates” section shows the five newest blog posts.

## Cloudflare Pages

This site is compatible with Cloudflare Pages because it builds to a static `dist/` directory.

Recommended settings:

- Build command: `npm run build`
- Build output directory: `dist`

You can also deploy with Wrangler using the included `wrangler.toml`.
