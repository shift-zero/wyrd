# SVG Export

`src/export_svg.py` — Vector map export. Produces SVG with:

- Color-coded terrain tiles as `<rect>` elements
- Settlement markers at map coordinates
- Annotated legend

Output: `wyrd-{seed}.svg`

## Usage

```bash
wyrd export --seed 42 --format svg -o my-world.svg
```

## See also

- [Export](export.md) — all export formats
- [CLI Reference](cli.md) — export command flags
