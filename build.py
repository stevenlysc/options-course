#!/usr/bin/env python3
"""Build options-course: render index + lesson pages, emit dist/worker.js.

Usage: python3 build.py
Reads manifest.json, lessons/<slug>.body.html, templates/.
"""
import json
import os

PROJ = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(PROJ, "dist")
PREFIX = "/options"


def main():
    manifest = json.load(open(os.path.join(PROJ, "manifest.json"),
                              encoding="utf-8"))
    lessons = manifest["lessons"]
    by_slug = {l["slug"]: l for l in lessons}

    lesson_tpl = open(os.path.join(PROJ, "templates", "lesson.html"),
                      encoding="utf-8").read()
    index_tpl = open(os.path.join(PROJ, "templates", "index.html"),
                     encoding="utf-8").read()

    pages = {}
    # --- index ---
    tiers_html = []
    done = 0
    for tier in ["预备", "Novice", "Intermediate", "Advanced", "Expert"]:
        tls = [l for l in lessons if l["tier"] == tier]
        rows = []
        for l in tls:
            if l["status"] == "published":
                done += 1
                rows.append(
                    f'<a class="lesson" href="{PREFIX}/{l["slug"]}">'
                    f'<span class="num">{l["n"]}</span>'
                    f'<span class="t"><span class="en">{l["en"]}</span><br>'
                    f'<span class="cn">{l["cn"]}</span></span>'
                    f'<span class="cat">{l["cat"]}</span>'
                    f'<span class="badge live">已发布</span></a>')
            else:
                rows.append(
                    f'<div class="lesson">'
                    f'<span class="num">{l["n"]}</span>'
                    f'<span class="t"><span class="en">{l["en"]}</span><br>'
                    f'<span class="cn">{l["cn"]}</span></span>'
                    f'<span class="cat">{l["cat"]}</span>'
                    f'<span class="badge soon">待更新</span></div>')
        tiers_html.append(
            f'<div class="tier">{tier}<span>{len(tls)} 节</span></div>\n'
            + "\n".join(rows))
    index_html = (index_tpl
                  .replace("{{TIERS}}", "\n".join(tiers_html))
                  .replace("{{TOTAL}}", str(len(lessons)))
                  .replace("{{DONE}}", str(done))
                  .replace("{{PCT}}", f"{done / len(lessons) * 100:.1f}"))

    # --- lesson pages ---
    published = [l for l in lessons if l["status"] == "published"]
    for i, l in enumerate(published):
        body_path = os.path.join(PROJ, "lessons", l["slug"] + ".body.html")
        body = open(body_path, encoding="utf-8").read()
        prev_l = published[i - 1] if i > 0 else None
        next_l = published[i + 1] if i + 1 < len(published) else None
        if prev_l:
            prev_link = (f'<a href="{PREFIX}/{prev_l["slug"]}">'
                         f'<span>‹ 上一课</span>第 {prev_l["n"]} 课 · '
                         f'{prev_l["en"]}</a>')
        else:
            prev_link = '<a class="disabled"><span>‹ 上一课</span>无</a>'
        if next_l:
            next_link = (f'<a class="next" href="{PREFIX}/{next_l["slug"]}">'
                         f'<span>下一课 ›</span>第 {next_l["n"]} 课 · '
                         f'{next_l["en"]}</a>')
        else:
            next_link = '<a class="next disabled"><span>下一课 ›</span>待更新</a>'
        html = (lesson_tpl
                .replace("{{PAGE_TITLE}}", f'第 {l["n"]} 课 · {l["en"]}')
                .replace("{{TOTAL}}", str(len(lessons)))
                .replace("{{N}}", str(l["n"]))
                .replace("{{BODY}}", body)
                .replace("{{PREV_LINK}}", prev_link)
                .replace("{{NEXT_LINK}}", next_link))
        pages[l["slug"]] = html

    # --- worker.js ---
    worker_js = (
        "const PREFIX = " + json.dumps(PREFIX) + ";\n"
        "const INDEX = " + json.dumps(index_html) + ";\n"
        "const PAGES = " + json.dumps(pages) + ";\n"
        "function html(body) {\n"
        "  return new Response(body, { headers: {\n"
        "    'content-type': 'text/html; charset=utf-8',\n"
        "    'cache-control': 'no-cache' }});\n"
        "}\n"
        "export default {\n"
        "  async fetch(request) {\n"
        "    const url = new URL(request.url);\n"
        "    let p = url.pathname;\n"
        "    if (p === PREFIX)\n"
        "      return Response.redirect(new URL(PREFIX + '/', url).toString(),\n"
        "                             301);\n"
        "    if (p.startsWith(PREFIX + '/')) p = p.slice(PREFIX.length);\n"
        "    else return new Response('Not found', { status: 404 });\n"
        "    if (p === '/' || p === '/index.html') return html(INDEX);\n"
        "    const slug = p.replace(/^\\//, '').replace(/\\/$/, '');\n"
        "    if (slug in PAGES) return html(PAGES[slug]);\n"
        "    return new Response('Not found', { status: 404 });\n"
        "  }\n"
        "};\n"
    )
    os.makedirs(DIST, exist_ok=True)
    open(os.path.join(DIST, "worker.js"), "w",
         encoding="utf-8").write(worker_js)
    print(f"built: {len(pages)} lesson pages, "
          f"worker.js {len(worker_js)} bytes")


if __name__ == "__main__":
    main()
