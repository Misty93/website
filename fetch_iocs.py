with open(index_path, "w", encoding="utf-8") as f:
    f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IOC Archive</title>

<link rel="stylesheet" href="/assets/style.css">
</head>

<body>

<div class="container">

<a class="back-link" href="/">← Back to homepage</a>

<h1>IOC Archive</h1>

<ul>
""")

    for d in entries:
        f.write(f"<li><a href='/daily-ioc/ioc-{d}/'>{d}</a></li>\n")

    f.write("""
</ul>

</div>

</body>
</html>
""")
