:: webui - Styled Web UI Components
::
:: Generates themed HTML/CSS components for KentScript web apps.
:: No external CSS needed — everything is self-contained.
::
:: Usage:
::   import webui;
::   let page = webui.page("My App", webui.dark_theme(), [
::       webui.navbar([{"text": "Home", "url": "/"}, {"text": "About", "url": "/about"}]),
::       webui.card("Welcome", "Hello from KentScript!"),
::       webui.table(["Name", "Age"], [["Alice", 30], ["Bob", 25]])
::   ]);
::   return web.html(page);

import web;
import json;

:: ─── Themes ──────────────────────────────────────────────────────────────

func dark_theme() {
    return {
        "bg": "#0d1117",
        "surface": "#161b22",
        "border": "#30363d",
        "text": "#e6edf3",
        "text_muted": "#8b949e",
        "primary": "#58a6ff",
        "primary_hover": "#79c0ff",
        "success": "#3fb950",
        "warning": "#d29922",
        "danger": "#f85149",
        "info": "#58a6ff",
        "radius": "8px",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    };
}

func light_theme() {
    return {
        "bg": "#ffffff",
        "surface": "#f6f8fa",
        "border": "#d0d7de",
        "text": "#1f2328",
        "text_muted": "#656d76",
        "primary": "#0969da",
        "primary_hover": "#0550ae",
        "success": "#1a7f37",
        "warning": "#9a6700",
        "danger": "#cf222e",
        "info": "#0969da",
        "radius": "6px",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    };
}

func midnight_theme() {
    return {
        "bg": "#0a0e1a",
        "surface": "#111827",
        "border": "#1e293b",
        "text": "#e2e8f0",
        "text_muted": "#94a3b8",
        "primary": "#818cf8",
        "primary_hover": "#a5b4fc",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#f87171",
        "info": "#818cf8",
        "radius": "10px",
        "font": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    };
}

func custom_theme(overrides) {
    let t = dark_theme();
    for key in overrides {
        t[key] = overrides[key];
    }
    return t;
}

:: ─── CSS Generator ──────────────────────────────────────────────────────

func _base_css(t) {
    return "
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: " + t["font"] + ";
    background: " + t["bg"] + ";
    color: " + t["text"] + ";
    line-height: 1.6;
    padding: 0;
}
.ks-container { max-width: 960px; margin: 0 auto; padding: 24px; }
.ks-container-wide { max-width: 1200px; margin: 0 auto; padding: 24px; }
a { color: " + t["primary"] + "; text-decoration: none; }
a:hover { color: " + t["primary_hover"] + "; text-decoration: underline; }
";
}

:: ─── Components ─────────────────────────────────────────────────────────

func navbar(links, brand, t) {
    if t == none { t = dark_theme(); }
    if brand == none { brand = "KentScript"; }

    let items = "";
    for link in links {
        items = items + "<a href='" + link["url"] + "' class='ks-nav-link'>" + link["text"] + "</a>";
    }

    return "
<nav class='ks-navbar'>
    <div class='ks-navbar-inner'>
        <span class='ks-navbar-brand'>" + brand + "</span>
        <div class='ks-navbar-links'>" + items + "</div>
    </div>
</nav>
<style>
.ks-navbar { background: " + t["surface"] + "; border-bottom: 1px solid " + t["border"] + "; padding: 12px 24px; }
.ks-navbar-inner { max-width: 1200px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; }
.ks-navbar-brand { font-size: 18px; font-weight: 700; color: " + t["primary"] + "; }
.ks-navbar-links { display: flex; gap: 20px; }
.ks-nav-link { color: " + t["text_muted"] + "; font-size: 14px; text-decoration: none; padding: 4px 0; }
.ks-nav-link:hover { color: " + t["text"] + "; text-decoration: none; }
</style>";
}

func card(title, body, t) {
    if t == none { t = dark_theme(); }

    return "
<div class='ks-card'>
    <div class='ks-card-title'>" + title + "</div>
    <div class='ks-card-body'>" + body + "</div>
</div>
<style>
.ks-card { background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 20px; margin-bottom: 16px; }
.ks-card-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; color: " + t["text"] + "; }
.ks-card-body { font-size: 14px; color: " + t["text_muted"] + "; }
</style>";
}

func button(text, url, variant, t) {
    if t == none { t = dark_theme(); }
    if variant == none { variant = "primary"; }

    let color = t["primary"];
    let hover = t["primary_hover"];
    if variant == "danger" { color = t["danger"]; hover = "#da3633"; }
    elif variant == "success" { color = t["success"]; hover = "#2ea043"; }
    elif variant == "warning" { color = t["warning"]; hover = "#bb8009"; }
    elif variant == "outline" { color = "transparent"; hover = t["surface"]; }

    let tag = "button";
    let href = "";
    if url != none { tag = "a"; href = " href='" + url + "'"; }

    let style = "";
    if variant == "outline" {
        style = " style='background:transparent;color:" + t["text"] + ";border:1px solid " + t["border"] + ";'";
    }

    return "<" + tag + href + " class='ks-btn ks-btn-" + variant + "'" + style + ">" + text + "</" + tag + ">
<style>
.ks-btn { display: inline-block; padding: 8px 16px; border-radius: " + t["radius"] + "; font-size: 14px; font-weight: 500; cursor: pointer; border: none; text-decoration: none; transition: background 0.2s; }
.ks-btn-primary { background: " + t["primary"] + "; color: #fff; }
.ks-btn-primary:hover { background: " + hover + "; text-decoration: none; }
.ks-btn-danger { background: " + t["danger"] + "; color: #fff; }
.ks-btn-success { background: " + t["success"] + "; color: #fff; }
.ks-btn-warning { background: " + t["warning"] + "; color: #fff; }
</style>";
}

func input(placeholder, input_type, name, t) {
    if t == none { t = dark_theme(); }
    if input_type == none { input_type = "text"; }
    if placeholder == none { placeholder = ""; }

    let nattr = "";
    if name != none { nattr = " name='" + name + "'"; }

    return "<input type='" + input_type + "' placeholder='" + placeholder + "'" + nattr + " class='ks-input' />
<style>
.ks-input { width: 100%; padding: 10px 14px; background: " + t["bg"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; color: " + t["text"] + "; font-size: 14px; margin-bottom: 12px; outline: none; transition: border-color 0.2s; }
.ks-input:focus { border-color: " + t["primary"] + "; }
.ks-input::placeholder { color: " + t["text_muted"] + "; }
</style>";
}

func textarea(placeholder, rows, name, t) {
    if t == none { t = dark_theme(); }
    if rows == none { rows = 4; }

    let nattr = "";
    if name != none { nattr = " name='" + name + "'"; }

    return "<textarea placeholder='" + placeholder + "' rows='" + str(rows) + "'" + nattr + " class='ks-textarea'></textarea>
<style>
.ks-textarea { width: 100%; padding: 10px 14px; background: " + t["bg"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; color: " + t["text"] + "; font-size: 14px; margin-bottom: 12px; outline: none; resize: vertical; font-family: inherit; }
.ks-textarea:focus { border-color: " + t["primary"] + "; }
</style>";
}

func table(headers, rows, t) {
    if t == none { t = dark_theme(); }

    let head = "";
    for h in headers {
        head = head + "<th class='ks-th'>" + h + "</th>";
    }

    let body = "";
    for row in rows {
        body = body + "<tr class='ks-tr'>";
        for cell in row {
            body = body + "<td class='ks-td'>" + str(cell) + "</td>";
        }
        body = body + "</tr>";
    }

    return "
<div class='ks-table-wrap'>
<table class='ks-table'>
<thead><tr>" + head + "</tr></thead>
<tbody>" + body + "</tbody>
</table>
</div>
<style>
.ks-table-wrap { overflow-x: auto; margin-bottom: 16px; }
.ks-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.ks-th { text-align: left; padding: 10px 14px; background: " + t["surface"] + "; border-bottom: 2px solid " + t["border"] + "; color: " + t["text_muted"] + "; font-weight: 600; }
.ks-td { padding: 10px 14px; border-bottom: 1px solid " + t["border"] + "; color: " + t["text"] + "; }
.ks-tr:hover .ks-td { background: " + t["surface"] + "; }
</style>";
}

func alert(msg, variant, t) {
    if t == none { t = dark_theme(); }
    if variant == none { variant = "info"; }

    let color = t["info"];
    let icon = "ℹ";
    if variant == "success" { color = t["success"]; icon = "✔"; }
    elif variant == "warning" { color = t["warning"]; icon = "⚠"; }
    elif variant == "danger" { color = t["danger"]; icon = "✖"; }

    return "
<div class='ks-alert ks-alert-" + variant + "'>
    <span class='ks-alert-icon'>" + icon + "</span>
    <span>" + msg + "</span>
</div>
<style>
.ks-alert { display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-radius: " + t["radius"] + "; border: 1px solid " + color + "; background: " + t["surface"] + "; margin-bottom: 12px; font-size: 14px; }
.ks-alert-icon { font-size: 16px; color: " + color + "; }
</style>";
}

func badge(text, color, t) {
    if t == none { t = dark_theme(); }
    if color == none { color = t["primary"]; }

    return "<span class='ks-badge' style='background:" + color + "'>" + text + "</span>
<style>
.ks-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; color: #fff; }
</style>";
}

func modal(title, body, id, t) {
    if t == none { t = dark_theme(); }
    if id == none { id = "ks-modal-1"; }

    return "
<div id='" + id + "' class='ks-modal-overlay' onclick='if(event.target===this)this.style.display=\"none\"'>
<div class='ks-modal'>
    <div class='ks-modal-header'>
        <span>" + title + "</span>
        <span class='ks-modal-close' onclick='document.getElementById(\"" + id + "\").style.display=\"none\"'>✖</span>
    </div>
    <div class='ks-modal-body'>" + body + "</div>
</div>
</div>
<style>
.ks-modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center; }
.ks-modal { background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; width: 480px; max-width: 90vw; }
.ks-modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid " + t["border"] + "; font-weight: 600; }
.ks-modal-close { cursor: pointer; color: " + t["text_muted"] + "; font-size: 18px; }
.ks-modal-body { padding: 20px; }
</style>";
}

func tabs(labels, contents, t) {
    if t == none { t = dark_theme(); }

    let tab_buttons = "";
    let tab_panels = "";
    for i in range(len(labels)) {
        let active = i == 0 ? " ks-tab-active" : "";
        let display = i == 0 ? "block" : "none";
        tab_buttons = tab_buttons + "<button class='ks-tab-btn" + active + "' onclick='ksTabSwitch(this," + str(i) + ")'>" + labels[i] + "</button>";
        tab_panels = tab_panels + "<div class='ks-tab-panel' style='display:" + display + "'>" + contents[i] + "</div>";
    }

    return "
<div class='ks-tabs'>
<div class='ks-tab-bar'>" + tab_buttons + "</div>
" + tab_panels + "
</div>
<script>
function ksTabSwitch(btn,idx){var tabs=btn.closest('.ks-tabs');tabs.querySelectorAll('.ks-tab-btn').forEach(function(b){b.classList.remove('ks-tab-active')});btn.classList.add('ks-tab-active');var panels=tabs.querySelectorAll('.ks-tab-panel');panels.forEach(function(p,i){p.style.display=i==idx?'block':'none'})}
</script>
<style>
.ks-tab-bar { display: flex; gap: 0; border-bottom: 1px solid " + t["border"] + "; margin-bottom: 16px; }
.ks-tab-btn { padding: 10px 20px; background: none; border: none; border-bottom: 2px solid transparent; color: " + t["text_muted"] + "; cursor: pointer; font-size: 14px; }
.ks-tab-btn.ks-tab-active { color: " + t["primary"] + "; border-bottom-color: " + t["primary"] + "; }
.ks-tab-panel { font-size: 14px; }
</style>";
}

func sidebar(links, brand, t) {
    if t == none { t = dark_theme(); }
    if brand == none { brand = "Menu"; }

    let items = "";
    for link in links {
        items = items + "<a href='" + link["url"] + "' class='ks-sidebar-link'>" + link["text"] + "</a>";
    }

    return "
<aside class='ks-sidebar'>
    <div class='ks-sidebar-brand'>" + brand + "</div>
    " + items + "
</aside>
<style>
.ks-sidebar { width: 240px; background: " + t["surface"] + "; border-right: 1px solid " + t["border"] + "; padding: 20px 0; min-height: 100vh; position: fixed; top: 0; left: 0; }
.ks-sidebar-brand { padding: 0 20px 16px; font-size: 16px; font-weight: 700; color: " + t["primary"] + "; border-bottom: 1px solid " + t["border"] + "; margin-bottom: 8px; }
.ks-sidebar-link { display: block; padding: 8px 20px; color: " + t["text_muted"] + "; font-size: 14px; text-decoration: none; }
.ks-sidebar-link:hover { color: " + t["text"] + "; background: " + t["bg"] + "; text-decoration: none; }
</style>";
}

func page(title, theme, content_parts) {
    if theme == none { theme = dark_theme(); }

    let css = _base_css(theme);
    let body = "";
    for part in content_parts {
        body = body + part;
    }

    return "<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>" + title + "</title>
    <style>" + css + "</style>
</head>
<body>" + body + "</body>
</html>";
}

func page_from_string(title, theme, html_content) {
    if theme == none { theme = dark_theme(); }
    let css = _base_css(theme);

    return "<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>" + title + "</title>
    <style>" + css + "</style>
</head>
<body>" + html_content + "</body>
</html>";
}

:: ─── NEW COMPONENTS ─────────────────────────────────────────────────────

func form(action, method, fields, t) {
    if t == none { t = dark_theme(); }
    if method == none { method = "POST"; }

    let fields_html = "";
    for f in fields {
        let ftype = "text";
        let fplaceholder = "";
        let fname = "";
        let flabel = "";
        let fvalue = "";
        if "type" in f { ftype = f["type"]; }
        if "placeholder" in f { fplaceholder = f["placeholder"]; }
        if "name" in f { fname = f["name"]; }
        if "label" in f { flabel = f["label"]; }
        if "value" in f { fvalue = f["value"]; }

        let input_html = "";
        if flabel != "" {
            input_html = input_html + "<label class='ks-form-label'>" + flabel + "</label>";
        }
        if ftype == "textarea" {
            let rows = 4;
            if "rows" in f { rows = f["rows"]; }
            input_html = input_html + "<textarea name='" + fname + "' placeholder='" + fplaceholder + "' rows='" + str(rows) + "' class='ks-input ks-textarea'>" + fvalue + "</textarea>";
        } elif ftype == "select" {
            let options = [];
            if "options" in f { options = f["options"]; }
            input_html = input_html + "<select name='" + fname + "' class='ks-input'>";
            for opt in options {
                let oval = opt;
                let otext = opt;
                if type(opt) == "dict" {
                    oval = opt["value"];
                    otext = opt["text"];
                }
                input_html = input_html + "<option value='" + oval + "'>" + otext + "</option>";
            }
            input_html = input_html + "</select>";
        } elif ftype == "checkbox" {
            input_html = input_html + "<div class='ks-form-check'><input type='checkbox' name='" + fname + "' value='" + fvalue + "' class='ks-form-checkbox' /> " + fplaceholder + "</div>";
        } elif ftype == "radio" {
            let options = [];
            if "options" in f { options = f["options"]; }
            for opt in options {
                input_html = input_html + "<div class='ks-form-check'><input type='radio' name='" + fname + "' value='" + opt + "' class='ks-form-radio' /> " + opt + "</div>";
            }
        } else {
            input_html = input_html + "<input type='" + ftype + "' name='" + fname + "' placeholder='" + fplaceholder + "' value='" + fvalue + "' class='ks-input' />";
        }
        fields_html = fields_html + "<div class='ks-form-group'>" + input_html + "</div>";
    }

    let action_attr = "";
    if action != none { action_attr = " action='" + action + "'"; }

    return "<form method='" + method + "'" + action_attr + " class='ks-form'>" + fields_html + "<button type='submit' class='ks-btn ks-btn-primary'>Submit</button></form>
<style>
.ks-form { max-width: 480px; }
.ks-form-group { margin-bottom: 16px; }
.ks-form-label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 6px; color: " + t["text"] + "; }
.ks-form-check { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 14px; color: " + t["text"] + "; }
.ks-form-checkbox, .ks-form-radio { accent-color: " + t["primary"] + "; }
</style>";
}

func dropdown(label, options, name, t) {
    if t == none { t = dark_theme(); }

    let opts = "";
    for opt in options {
        let oval = opt;
        let otext = opt;
        if type(opt) == "dict" {
            oval = opt["value"];
            otext = opt["text"];
        }
        opts = opts + "<option value='" + oval + "'>" + otext + "</option>";
    }

    let nattr = "";
    if name != none { nattr = " name='" + name + "'"; }

    return "<select class='ks-dropdown'" + nattr + ">\n" + opts + "\n</select>
<style>
.ks-dropdown { width: 100%; padding: 10px 14px; background: " + t["bg"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; color: " + t["text"] + "; font-size: 14px; outline: none; appearance: none; background-image: url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%238b949e' d='M6 8L1 3h10z'/%3E%3C/svg%3E\"); background-repeat: no-repeat; background-position: right 12px center; cursor: pointer; }
.ks-dropdown:focus { border-color: " + t["primary"] + "; }
</style>";
}

func progress_bar(value, max_val, color, label, t) {
    if t == none { t = dark_theme(); }
    if max_val == none { max_val = 100; }
    if color == none { color = t["primary"]; }

    let pct = value * 100 / max_val;
    if pct > 100 { pct = 100; }
    if pct < 0 { pct = 0; }

    let label_html = "";
    if label != none { label_html = "<div class='ks-progress-label'>" + label + " — " + str(int(pct)) + "%</div>"; }

    return "
<div class='ks-progress-wrap'>
    " + label_html + "
    <div class='ks-progress-track'>
        <div class='ks-progress-fill' style='width:" + str(int(pct)) + "%;background:" + color + "'></div>
    </div>
</div>
<style>
.ks-progress-wrap { margin-bottom: 16px; }
.ks-progress-label { font-size: 13px; color: " + t["text_muted"] + "; margin-bottom: 6px; }
.ks-progress-track { width: 100%; height: 8px; background: " + t["border"] + "; border-radius: 4px; overflow: hidden; }
.ks-progress-fill { height: 100%; border-radius: 4px; transition: width 0.3s ease; }
</style>";
}

func tooltip(text, target_html, position, t) {
    if t == none { t = dark_theme(); }
    if position == none { position = "top"; }
    let id = "ks-tip-" + str(system_time() % 99999);

    let style = "";
    if position == "top" {
        style = "bottom:100%;left:50%;transform:translateX(-50%);margin-bottom:8px;";
    } elif position == "bottom" {
        style = "top:100%;left:50%;transform:translateX(-50%);margin-top:8px;";
    } elif position == "left" {
        style = "right:100%;top:50%;transform:translateY(-50%);margin-right:8px;";
    } elif position == "right" {
        style = "left:100%;top:50%;transform:translateY(-50%);margin-left:8px;";
    }

    return "<span class='ks-tooltip-wrap'>" + target_html + "<span class='ks-tooltip' style='" + style + "'>" + text + "</span></span>
<style>
.ks-tooltip-wrap { position: relative; display: inline-block; }
.ks-tooltip { display: none; position: absolute; background: " + t["text"] + "; color: " + t["bg"] + "; padding: 6px 10px; border-radius: 4px; font-size: 12px; white-space: nowrap; z-index: 999; pointer-events: none; }
.ks-tooltip-wrap:hover .ks-tooltip { display: block; }
</style>";
}

func accordion(items, t) {
    if t == none { t = dark_theme(); }

    let panels = "";
    for i in range(len(items)) {
        let item = items[i];
        let title = item["title"];
        let content = item["content"];
        let id = "ks-acc-" + str(i);
        panels = panels + "
<div class='ks-accordion-item'>
    <button class='ks-accordion-header' onclick='ksAccToggle(\"" + id + "\")'>" + title + "</button>
    <div id='" + id + "' class='ks-accordion-body'>" + content + "</div>
</div>";
    }

    return panels + "
<script>
function ksAccToggle(id){var el=document.getElementById(id);el.style.display=el.style.display==='block'?'none':'block';}
</script>
<style>
.ks-accordion-item { border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; margin-bottom: 8px; overflow: hidden; }
.ks-accordion-header { width: 100%; padding: 14px 18px; background: " + t["surface"] + "; border: none; color: " + t["text"] + "; font-size: 14px; font-weight: 500; text-align: left; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
.ks-accordion-header:hover { background: " + t["bg"] + "; }
.ks-accordion-body { display: none; padding: 0 18px 14px; font-size: 14px; color: " + t["text_muted"] + "; }
</style>";
}

func toast(msg, duration, variant, t) {
    if t == none { t = dark_theme(); }
    if duration == none { duration = 3000; }
    if variant == none { variant = "info"; }
    let id = "ks-toast-" + str(system_time() % 99999);
    let color = t["primary"];
    let icon = "ℹ";
    if variant == "success" { color = t["success"]; icon = "✔"; }
    elif variant == "warning" { color = t["warning"]; icon = "⚠"; }
    elif variant == "danger" { color = t["danger"]; icon = "✖"; }

    return "
<div id='" + id + "' class='ks-toast ks-toast-" + variant + "'>
    <span class='ks-toast-icon'>" + icon + "</span>
    <span>" + msg + "</span>
</div>
<script>
(function(){var t=document.getElementById('" + id + "');if(t){t.style.display='flex';setTimeout(function(){t.style.opacity='0';setTimeout(function(){t.remove()},300)}," + str(duration) + ");}})();
</script>
<style>
.ks-toast { display: none; position: fixed; top: 20px; right: 20px; padding: 12px 20px; border-radius: " + t["radius"] + "; background: " + t["surface"] + "; border: 1px solid " + color + "; color: " + t["text"] + "; font-size: 14px; gap: 10px; align-items: center; z-index: 9999; box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: opacity 0.3s; }
.ks-toast-icon { font-size: 16px; color: " + color + "; }
</style>";
}

func pagination(current, total_pages, base_url, t) {
    if t == none { t = dark_theme(); }
    if total_pages <= 1 { return ""; }

    let items = "";
    let max_show = 7;
    let start = current - 3;
    let end = current + 3;
    if start < 1 { start = 1; }
    if end > total_pages { end = total_pages; }

    let sep = "?";
    if base_url.contains("?") { sep = "&"; }

    if current > 1 {
        items = items + "<a href='" + base_url + sep + "page=" + str(current - 1) + "' class='ks-page-btn'>← Prev</a>";
    }
    for i in range(start, end + 1) {
        let active = "";
        if i == current { active = " ks-page-active"; }
        items = items + "<a href='" + base_url + sep + "page=" + str(i) + "' class='ks-page-btn" + active + "'>" + str(i) + "</a>";
    }
    if current < total_pages {
        items = items + "<a href='" + base_url + sep + "page=" + str(current + 1) + "' class='ks-page-btn'>Next →</a>";
    }

    return "<div class='ks-pagination'>" + items + "</div>
<style>
.ks-pagination { display: flex; gap: 4px; margin-bottom: 16px; }
.ks-page-btn { padding: 8px 14px; border-radius: " + t["radius"] + "; font-size: 14px; color: " + t["text"] + "; background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; text-decoration: none; transition: all 0.2s; }
.ks-page-btn:hover { background: " + t["primary"] + "; color: #fff; border-color: " + t["primary"] + "; text-decoration: none; }
.ks-page-active { background: " + t["primary"] + "; color: #fff; border-color: " + t["primary"] + "; }
</style>";
}

func footer(links, brand, copyright, t) {
    if t == none { t = dark_theme(); }
    if brand == none { brand = "KentScript"; }

    let items = "";
    if links != none {
        for link in links {
            items = items + "<a href='" + link["url"] + "' class='ks-footer-link'>" + link["text"] + "</a>";
        }
    }

    let copy_text = "";
    if copyright != none { copy_text = copyright; }

    return "
<footer class='ks-footer'>
    <div class='ks-footer-inner'>
        <span class='ks-footer-brand'>" + brand + "</span>
        <div class='ks-footer-links'>" + items + "</div>
        <span class='ks-footer-copy'>" + copy_text + "</span>
    </div>
</footer>
<style>
.ks-footer { background: " + t["surface"] + "; border-top: 1px solid " + t["border"] + "; padding: 20px 24px; margin-top: 40px; }
.ks-footer-inner { max-width: 1200px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.ks-footer-brand { font-size: 14px; font-weight: 600; color: " + t["primary"] + "; }
.ks-footer-links { display: flex; gap: 16px; }
.ks-footer-link { color: " + t["text_muted"] + "; font-size: 13px; text-decoration: none; }
.ks-footer-link:hover { color: " + t["text"] + "; text-decoration: underline; }
.ks-footer-copy { font-size: 12px; color: " + t["text_muted"] + "; }
</style>";
}

func dropdown_menu(label, items, t) {
    if t == none { t = dark_theme(); }
    let id = "ks-dmenu-" + str(system_time() % 99999);

    let menu_items = "";
    for item in items {
        if item == "-" {
            menu_items = menu_items + "<div class='ks-menu-sep'></div>";
        } else {
            let onclick = "";
            if "url" in item {
                onclick = "window.location='" + item["url"] + "'";
            } elif "onclick" in item {
                onclick = item["onclick"];
            }
            menu_items = menu_items + "<div class='ks-menu-item' onclick='" + onclick + "'>" + item["text"] + "</div>";
        }
    }

    return "
<div class='ks-dmenu-wrap' id='" + id + "'>
    <button class='ks-dmenu-btn' onclick='ksDmenuToggle(\"" + id + "\")'>" + label + " ▾</button>
    <div id='" + id + "-menu' class='ks-dmenu'>" + menu_items + "</div>
</div>
<script>
function ksDmenuToggle(id){var m=document.getElementById(id+'-menu');m.style.display=m.style.display==='block'?'none':'block';}
document.addEventListener('click',function(e){var w=document.getElementById('" + id + "');if(w&&!w.contains(e.target)){document.getElementById('" + id + "-menu').style.display='none';}});
</script>
<style>
.ks-dmenu-wrap { position: relative; display: inline-block; }
.ks-dmenu-btn { padding: 8px 16px; background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; color: " + t["text"] + "; font-size: 14px; cursor: pointer; }
.ks-dmenu-btn:hover { background: " + t["bg"] + "; }
.ks-dmenu { display: none; position: absolute; top: 100%; left: 0; min-width: 180px; background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; box-shadow: 0 8px 24px rgba(0,0,0,0.3); z-index: 100; margin-top: 4px; overflow: hidden; }
.ks-menu-item { padding: 10px 16px; font-size: 14px; color: " + t["text"] + "; cursor: pointer; }
.ks-menu-item:hover { background: " + t["bg"] + "; color: " + t["primary"] + "; }
.ks-menu-sep { height: 1px; background: " + t["border"] + "; margin: 4px 0; }
</style>";
}

func code_block(code, lang, t) {
    if t == none { t = dark_theme(); }
    if lang == none { lang = ""; }

    let lang_badge = "";
    if lang != "" {
        lang_badge = "<span class='ks-code-lang'>" + lang + "</span>";
    }

    return "
<div class='ks-code-block'>
    " + lang_badge + "
    <pre class='ks-code-pre'><code>" + code + "</code></pre>
</div>
<style>
.ks-code-block { position: relative; background: " + t["bg"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; margin-bottom: 16px; overflow: hidden; }
.ks-code-lang { position: absolute; top: 8px; right: 12px; font-size: 11px; padding: 2px 8px; border-radius: 4px; background: " + t["border"] + "; color: " + t["text_muted"] + "; text-transform: uppercase; font-weight: 600; }
.ks-code-pre { padding: 16px; overflow-x: auto; font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace; font-size: 13px; line-height: 1.5; color: " + t["text"] + "; margin: 0; }
</style>";
}

func stat_card(value, label, icon, color, t) {
    if t == none { t = dark_theme(); }
    if color == none { color = t["primary"]; }

    let icon_html = "";
    if icon != none { icon_html = "<span class='ks-stat-icon' style='color:" + color + "'>" + icon + "</span>"; }

    return "
<div class='ks-stat-card'>
    " + icon_html + "
    <div class='ks-stat-value'>" + str(value) + "</div>
    <div class='ks-stat-label'>" + label + "</div>
</div>
<style>
.ks-stat-card { background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 20px; text-align: center; min-width: 140px; }
.ks-stat-icon { font-size: 24px; display: block; margin-bottom: 8px; }
.ks-stat-value { font-size: 28px; font-weight: 700; color: " + t["text"] + "; line-height: 1.2; }
.ks-stat-label { font-size: 13px; color: " + t["text_muted"] + "; margin-top: 4px; }
</style>";
}

func divider(text, t) {
    if t == none { t = dark_theme(); }
    if text == none {
        return "<hr class='ks-divider' />
<style>.ks-divider { border: none; border-top: 1px solid " + t["border"] + "; margin: 24px 0; }</style>";
    }
    return "<div class='ks-divider-wrap'><span class='ks-divider-text'>" + text + "</span></div>
<style>
.ks-divider-wrap { display: flex; align-items: center; margin: 24px 0; }
.ks-divider-wrap::before, .ks-divider-wrap::after { content: ''; flex: 1; border-top: 1px solid " + t["border"] + "; }
.ks-divider-text { padding: 0 16px; font-size: 13px; color: " + t["text_muted"] + "; text-transform: uppercase; letter-spacing: 0.5px; }
</style>";
}

func avatar(src, name, size, t) {
    if t == none { t = dark_theme(); }
    if size == none { size = 40; }
    let num_size = 40;
    if type(size) == "int" { num_size = size; }
    elif type(size) == "float" { num_size = int(size); }
    elif type(size) == "str" {
        let cleaned = size.replace("px", "");
        num_size = int(cleaned);
    }
    let initials = "";
    if name != none and name != "" {
        let parts = name.split(" ");
        for p in parts {
            if p != "" { initials = initials + p[0].upper(); }
            if len(initials) >= 2 { break; }
        }
    }

    if src != none {
        return "<img class='ks-avatar' src='" + src + "' alt='" + name + "' style='width:" + str(num_size) + "px;height:" + str(num_size) + "px' />
<style>.ks-avatar { border-radius: 50%; object-fit: cover; border: 2px solid " + t["border"] + "; }</style>";
    }
    return "<div class='ks-avatar ks-avatar-initials' style='width:" + str(num_size) + "px;height:" + str(num_size) + "px;background:" + t["primary"] + "'>" + initials + "</div>
<style>.ks-avatar-initials { border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 600; font-size: " + str(num_size // 2) + "px; }</style>";
}

func toggle(label, name, checked, t) {
    if t == none { t = dark_theme(); }
    if checked == none { checked = false; }
    let check_attr = "";
    if checked == true { check_attr = " checked"; }

    return "<label class='ks-toggle-wrap'>
    <input type='checkbox' class='ks-toggle-input' name='" + name + "'" + check_attr + " />
    <span class='ks-toggle-slider'></span>
    <span class='ks-toggle-label'>" + label + "</span>
</label>
<style>
.ks-toggle-wrap { display: inline-flex; align-items: center; gap: 10px; cursor: pointer; font-size: 14px; color: " + t["text"] + "; }
.ks-toggle-input { display: none; }
.ks-toggle-slider { width: 40px; height: 22px; background: " + t["border"] + "; border-radius: 11px; position: relative; transition: background 0.2s; }
.ks-toggle-slider::after { content: ''; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; background: #fff; border-radius: 50%; transition: transform 0.2s; }
.ks-toggle-input:checked + .ks-toggle-slider { background: " + t["primary"] + "; }
.ks-toggle-input:checked + .ks-toggle-slider::after { transform: translateX(18px); }
</style>";
}

func skeleton(lines, t) {
    if t == none { t = dark_theme(); }

    let items = "";
    for i in range(lines) {
        let width = "100%";
        if i == lines - 1 { width = "60%"; }
        items = items + "<div class='ks-skel-line' style='width:" + width + "'></div>";
    }

    return "<div class='ks-skeleton'>" + items + "</div>
<style>
.ks-skeleton { padding: 4px 0; }
.ks-skel-line { height: 14px; border-radius: 4px; background: linear-gradient(90deg, " + t["border"] + " 25%, " + t["surface"] + " 50%, " + t["border"] + " 75%); background-size: 200% 100%; animation: ks-shimmer 1.5s infinite; margin-bottom: 12px; }
@keyframes ks-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
</style>";
}

:: ─── ADVANCED COMPONENTS ───────────────────────────────────────────────────

func hero(title, subtitle, actions, t) {
    if t == none { t = dark_theme(); }
    if subtitle == none { subtitle = ""; }

    let btns = "";
    if actions != none {
        for act in actions {
            let variant = "primary";
            if "variant" in act { variant = act["variant"]; }
            btns = btns + button(act["text"], act["url"], variant, t);
        }
    }

    return "
<div class='ks-hero'>
    <div class='ks-hero-inner'>
        <h1 class='ks-hero-title'>" + title + "</h1>
        <p class='ks-hero-sub'>" + subtitle + "</p>
        <div class='ks-hero-actions'>" + btns + "</div>
    </div>
</div>
<style>
.ks-hero { background: linear-gradient(135deg, " + t["surface"] + " 0%, " + t["bg"] + " 100%); border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 60px 40px; text-align: center; margin-bottom: 24px; }
.ks-hero-title { font-size: 36px; font-weight: 800; color: " + t["text"] + "; margin-bottom: 12px; line-height: 1.2; }
.ks-hero-sub { font-size: 18px; color: " + t["text_muted"] + "; margin-bottom: 24px; max-width: 600px; margin-left: auto; margin-right: auto; }
.ks-hero-actions { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
</style>";
}

func feature_grid(features, cols, t) {
    if t == none { t = dark_theme(); }
    if cols == none { cols = 3; }

    let items = "";
    for f in features {
        let icon = "";
        if "icon" in f { icon = "<div class='ks-feature-icon' style='color:" + t["primary"] + "'>" + f["icon"] + "</div>"; }
        let desc = "";
        if "desc" in f { desc = "<div class='ks-feature-desc'>" + f["desc"] + "</div>"; }
        items = items + "
<div class='ks-feature-item'>
    " + icon + "
    <div class='ks-feature-title'>" + f["title"] + "</div>
    " + desc + "
</div>";
    }

    return "
<div class='ks-feature-grid' style='grid-template-columns: repeat(" + str(cols) + ", 1fr);'>
" + items + "
</div>
<style>
.ks-feature-grid { display: grid; gap: 20px; margin-bottom: 24px; }
.ks-feature-item { background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 24px; text-align: center; transition: transform 0.2s, border-color 0.2s; }
.ks-feature-item:hover { transform: translateY(-2px); border-color: " + t["primary"] + "; }
.ks-feature-icon { font-size: 32px; margin-bottom: 12px; }
.ks-feature-title { font-size: 16px; font-weight: 600; color: " + t["text"] + "; margin-bottom: 8px; }
.ks-feature-desc { font-size: 14px; color: " + t["text_muted"] + "; line-height: 1.5; }
</style>";
}

func pricing_table(plans, t) {
    if t == none { t = dark_theme(); }

    let cards = "";
    for p in plans {
        let features_html = "";
        let feats = p["features"];
        for f in feats {
            features_html = features_html + "<div class='ks-price-feature'>✔ " + f + "</div>";
        }
        let btn_variant = "outline";
        if "highlight" in p and p["highlight"] == true { btn_variant = "primary"; }
        let badge_html = "";
        if "badge" in p { badge_html = "<div class='ks-price-badge' style='background:" + t["primary"] + "'>" + p["badge"] + "</div>"; }
        let period = "mo";
        if "period" in p { period = p["period"]; }

        cards = cards + "
<div class='ks-price-card'>
    " + badge_html + "
    <div class='ks-price-name'>" + p["name"] + "</div>
    <div class='ks-price-amount'>" + p["price"] + "<span class='ks-price-period'>/" + period + "</span></div>
    <div class='ks-price-desc'>" + p["desc"] + "</div>
    <div class='ks-price-features'>" + features_html + "</div>
    " + button(p["cta"], p["cta_url"], btn_variant, t) + "
</div>";
    }

    return "
<div class='ks-pricing-grid'>
" + cards + "
</div>
<style>
.ks-pricing-grid { display: grid; grid-template-columns: repeat(" + str(len(plans)) + ", 1fr); gap: 20px; margin-bottom: 24px; align-items: start; }
.ks-price-card { background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 32px 24px; text-align: center; position: relative; transition: transform 0.2s; }
.ks-price-card:hover { transform: translateY(-4px); }
.ks-price-badge { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); padding: 4px 16px; border-radius: 12px; font-size: 12px; font-weight: 600; color: #fff; white-space: nowrap; }
.ks-price-name { font-size: 18px; font-weight: 700; color: " + t["text"] + "; margin-bottom: 8px; }
.ks-price-amount { font-size: 40px; font-weight: 800; color: " + t["text"] + "; margin-bottom: 4px; }
.ks-price-period { font-size: 16px; font-weight: 400; color: " + t["text_muted"] + "; }
.ks-price-desc { font-size: 14px; color: " + t["text_muted"] + "; margin-bottom: 20px; }
.ks-price-features { text-align: left; margin-bottom: 24px; }
.ks-price-feature { font-size: 14px; color: " + t["text"] + "; padding: 6px 0; border-bottom: 1px solid " + t["border"] + "; }
.ks-price-feature:last-child { border-bottom: none; }
</style>";
}

func testimonial(quote, author, role, avatar_url, t) {
    if t == none { t = dark_theme(); }

    let avatar_html = "";
    if avatar_url != none {
        avatar_html = "<img class='ks-testi-avatar' src='" + avatar_url + "' />";
    } elif role != none {
        let initials = "";
        let parts = author.split(" ");
        for p in parts {
            if p != "" { initials = initials + p[0].upper(); }
            if len(initials) >= 2 { break; }
        }
        avatar_html = "<div class='ks-testi-avatar ks-testi-initials' style='background:" + t["primary"] + "'>" + initials + "</div>";
    }

    return "
<div class='ks-testimonial'>
    <div class='ks-testi-quote'>&ldquo;" + quote + "&rdquo;</div>
    <div class='ks-testi-author'>
        " + avatar_html + "
        <div>
            <div class='ks-testi-name'>" + author + "</div>
            " + (role != none ? "<div class='ks-testi-role'>" + role + "</div>" : "") + "
        </div>
    </div>
</div>
<style>
.ks-testimonial { background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 28px; margin-bottom: 16px; }
.ks-testi-quote { font-size: 16px; color: " + t["text"] + "; line-height: 1.6; font-style: italic; margin-bottom: 20px; }
.ks-testi-quote::before { content: '\u201C'; font-size: 40px; color: " + t["primary"] + "; line-height: 0; vertical-align: -14px; margin-right: 4px; }
.ks-testi-author { display: flex; align-items: center; gap: 12px; }
.ks-testi-avatar { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; }
.ks-testi-initials { display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 600; font-size: 16px; }
.ks-testi-name { font-size: 14px; font-weight: 600; color: " + t["text"] + "; }
.ks-testi-role { font-size: 13px; color: " + t["text_muted"] + "; }
</style>";
}

func timeline(items, t) {
    if t == none { t = dark_theme(); }

    let entries = "";
    for i in range(len(items)) {
        let item = items[i];
        let dot_color = t["primary"];
        if "color" in item { dot_color = item["color"]; }
        let time_str = "";
        if "time" in item { time_str = "<div class='ks-tl-time'>" + item["time"] + "</div>"; }
        entries = entries + "
<div class='ks-tl-item'>
    <div class='ks-tl-dot' style='background:" + dot_color + "'></div>
    <div class='ks-tl-content'>
        <div class='ks-tl-title'>" + item["title"] + "</div>
        " + time_str + "
        <div class='ks-tl-desc'>" + item["desc"] + "</div>
    </div>
</div>";
    }

    return "
<div class='ks-timeline'>" + entries + "</div>
<style>
.ks-timeline { position: relative; padding-left: 28px; margin-bottom: 24px; }
.ks-timeline::before { content: ''; position: absolute; left: 8px; top: 0; bottom: 0; width: 2px; background: " + t["border"] + "; }
.ks-tl-item { position: relative; margin-bottom: 24px; }
.ks-tl-dot { position: absolute; left: -24px; top: 4px; width: 12px; height: 12px; border-radius: 50%; border: 2px solid " + t["surface"] + "; }
.ks-tl-title { font-size: 15px; font-weight: 600; color: " + t["text"] + "; }
.ks-tl-time { font-size: 12px; color: " + t["text_muted"] + "; margin-bottom: 4px; }
.ks-tl-desc { font-size: 14px; color: " + t["text_muted"] + "; line-height: 1.5; margin-top: 4px; }
</style>";
}

func steps(labels, current, t) {
    if t == none { t = dark_theme(); }

    let items = "";
    for i in range(len(labels)) {
        let state = "pending";
        if i < current { state = "done"; }
        elif i == current { state = "active"; }
        let color = t["border"];
        if state == "done" { color = t["success"]; }
        elif state == "active" { color = t["primary"]; }
        let num = str(i + 1);
        if state == "done" { num = "✔"; }
        items = items + "
<div class='ks-step'>
    <div class='ks-step-circle' style='background:" + color + ";color:#fff'>" + num + "</div>
    <div class='ks-step-label' style='color:" + (state == "pending" ? t["text_muted"] : t["text"]) + "'>" + labels[i] + "</div>
</div>";
    }

    return "
<div class='ks-steps'>" + items + "</div>
<style>
.ks-steps { display: flex; align-items: center; margin-bottom: 24px; }
.ks-step { display: flex; flex-direction: column; align-items: center; flex: 1; position: relative; }
.ks-step::after { content: ''; position: absolute; top: 16px; left: 50%; width: 100%; height: 2px; background: " + t["border"] + "; z-index: 0; }
.ks-step:last-child::after { display: none; }
.ks-step-circle { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; z-index: 1; position: relative; }
.ks-step-label { font-size: 13px; margin-top: 8px; text-align: center; }
</style>";
}

func chart_bar(data, max_val, t) {
    if t == none { t = dark_theme(); }
    if max_val == none { max_val = 0; }

    let bars = "";
    let colors = [t["primary"], t["success"], t["warning"], t["danger"], t["info"]];
    for i in range(len(data)) {
        let item = data[i];
        let val = item["value"];
        let label = item["label"];
        if max_val == 0 and val > max_val { max_val = val; }
        let pct = 0;
        if max_val > 0 { pct = val * 100 / max_val; }
        let color = colors[i % len(colors)];
        bars = bars + "
<div class='ks-bar-row'>
    <div class='ks-bar-label'>" + label + "</div>
    <div class='ks-bar-track'>
        <div class='ks-bar-fill' style='width:" + str(int(pct)) + "%;background:" + color + "'></div>
    </div>
    <div class='ks-bar-value'>" + str(val) + "</div>
</div>";
    }

    return "
<div class='ks-chart-bar'>" + bars + "</div>
<style>
.ks-chart-bar { margin-bottom: 24px; }
.ks-bar-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.ks-bar-label { width: 100px; font-size: 14px; color: " + t["text"] + "; text-align: right; flex-shrink: 0; }
.ks-bar-track { flex: 1; height: 24px; background: " + t["border"] + "; border-radius: 4px; overflow: hidden; }
.ks-bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
.ks-bar-value { width: 50px; font-size: 14px; font-weight: 600; color: " + t["text"] + "; }
</style>";
}

func breadcrumbs(items, t) {
    if t == none { t = dark_theme(); }

    let crumbs = "";
    for i in range(len(items)) {
        let item = items[i];
        let sep = " / ";
        if i == len(items) - 1 { sep = ""; }
        if "url" in item {
            crumbs = crumbs + "<a href='" + item["url"] + "' class='ks-bc-link'>" + item["text"] + "</a>" + sep;
        } else {
            crumbs = crumbs + "<span class='ks-bc-current'>" + item["text"] + "</span>" + sep;
        }
    }

    return "
<nav class='ks-breadcrumbs'>" + crumbs + "</nav>
<style>
.ks-breadcrumbs { font-size: 14px; margin-bottom: 16px; padding: 10px 16px; background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; }
.ks-bc-link { color: " + t["primary"] + "; text-decoration: none; }
.ks-bc-link:hover { text-decoration: underline; }
.ks-bc-current { color: " + t["text_muted"] + "; }
</style>";
}

func team_card(name, role, bio, avatar_url, socials, t) {
    if t == none { t = dark_theme(); }

    let initials = "";
    let parts = name.split(" ");
    for p in parts {
        if p != "" { initials = initials + p[0].upper(); }
        if len(initials) >= 2 { break; }
    }

    let avatar_html = "";
    if avatar_url != none {
        avatar_html = "<img class='ks-team-avatar' src='" + avatar_url + "' />";
    } else {
        avatar_html = "<div class='ks-team-avatar ks-team-initials' style='background:" + t["primary"] + "'>" + initials + "</div>";
    }

    let social_html = "";
    if socials != none {
        for s in socials {
            social_html = social_html + "<a href='" + s["url"] + "' class='ks-team-social' target='_blank'>" + s["icon"] + "</a>";
        }
    }

    return "
<div class='ks-team-card'>
    " + avatar_html + "
    <div class='ks-team-name'>" + name + "</div>
    <div class='ks-team-role' style='color:" + t["primary"] + "'>" + role + "</div>
    <div class='ks-team-bio'>" + bio + "</div>
    <div class='ks-team-socials'>" + social_html + "</div>
</div>
<style>
.ks-team-card { background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 28px; text-align: center; transition: transform 0.2s; }
.ks-team-card:hover { transform: translateY(-4px); }
.ks-team-avatar { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; margin-bottom: 16px; }
.ks-team-initials { display: inline-flex; align-items: center; justify-content: center; color: #fff; font-size: 28px; font-weight: 700; }
.ks-team-name { font-size: 18px; font-weight: 700; color: " + t["text"] + "; margin-bottom: 4px; }
.ks-team-role { font-size: 14px; font-weight: 500; margin-bottom: 12px; }
.ks-team-bio { font-size: 14px; color: " + t["text_muted"] + "; line-height: 1.5; margin-bottom: 16px; }
.ks-team-socials { display: flex; gap: 12px; justify-content: center; }
.ks-team-social { color: " + t["text_muted"] + "; font-size: 18px; text-decoration: none; }
.ks-team-social:hover { color: " + t["primary"] + "; }
</style>";
}

func chat_bubble(text, sender, time, is_me, t) {
    if t == none { t = dark_theme(); }

    let bg = t["surface"];
    let align = "flex-start";
    let border_style = "border-radius: " + t["radius"] + " " + t["radius"] + " " + t["radius"] + " 0;";
    if is_me == true {
        bg = t["primary"];
        align = "flex-end";
        border_style = "border-radius: " + t["radius"] + " " + t["radius"] + " 0 " + t["radius"] + ";";
    }
    let time_html = "";
    if time != none { time_html = "<div class='ks-chat-time'>" + time + "</div>"; }

    return "
<div class='ks-chat-row' style='justify-content:" + align + "'>
    <div class='ks-chat-bubble' style='background:" + bg + ";" + border_style + "'>" + text + "</div>
</div>
" + time_html;
}

func chat(messages, t) {
    if t == none { t = dark_theme(); }

    let bubbles = "";
    for msg in messages {
        let is_me = false;
        if "me" in msg { is_me = msg["me"]; }
        bubbles = bubbles + chat_bubble(msg["text"], msg["sender"], msg["time"], is_me, t);
    }

    return "
<div class='ks-chat'>" + bubbles + "</div>
<style>
.ks-chat { display: flex; flex-direction: column; gap: 8px; margin-bottom: 24px; padding: 16px; background: " + t["bg"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; max-height: 400px; overflow-y: auto; }
.ks-chat-row { display: flex; }
.ks-chat-bubble { max-width: 70%; padding: 10px 16px; font-size: 14px; color: " + t["text"] + "; line-height: 1.5; word-wrap: break-word; }
.ks-chat-time { font-size: 11px; color: " + t["text_muted"] + "; margin-top: 4px; margin-bottom: 8px; }
.ks-chat-row:last-child .ks-chat-time { display: none; }
</style>";
}

func login_form(title, t) {
    if t == none { t = dark_theme(); }
    if title == none { title = "Sign In"; }

    return "
<div class='ks-auth-card'>
    <div class='ks-auth-title'>" + title + "</div>
    <form method='POST' class='ks-auth-form'>
        <label class='ks-form-label'>Email</label>
        <input type='email' name='email' placeholder='you@example.com' class='ks-input' />
        <label class='ks-form-label'>Password</label>
        <input type='password' name='password' placeholder='Enter password' class='ks-input' />
        <div class='ks-auth-row'>
            <label class='ks-form-check'><input type='checkbox' class='ks-form-checkbox' /> Remember me</label>
            <a href='#' style='font-size:13px'>Forgot password?</a>
        </div>
        <button type='submit' class='ks-btn ks-btn-primary' style='width:100%'>Sign In</button>
    </form>
    <div class='ks-auth-footer'>Don't have an account? <a href='#'>Sign up</a></div>
</div>
<style>
.ks-auth-card { max-width: 400px; margin: 0 auto; background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 32px; }
.ks-auth-title { font-size: 24px; font-weight: 700; color: " + t["text"] + "; text-align: center; margin-bottom: 24px; }
.ks-auth-form { display: flex; flex-direction: column; gap: 4px; }
.ks-auth-row { display: flex; justify-content: space-between; align-items: center; font-size: 13px; margin-bottom: 16px; }
.ks-auth-row a { color: " + t["primary"] + "; text-decoration: none; }
.ks-auth-footer { text-align: center; margin-top: 16px; font-size: 14px; color: " + t["text_muted"] + "; }
.ks-auth-footer a { color: " + t["primary"] + "; text-decoration: none; }
</style>";
}

func search_bar(placeholder, t) {
    if t == none { t = dark_theme(); }
    if placeholder == none { placeholder = "Search..."; }

    return "
<div class='ks-search-wrap'>
    <span class='ks-search-icon'>🔍</span>
    <input type='text' placeholder='" + placeholder + "' class='ks-search-input' />
</div>
<style>
.ks-search-wrap { position: relative; margin-bottom: 16px; }
.ks-search-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); font-size: 14px; pointer-events: none; }
.ks-search-input { width: 100%; padding: 12px 14px 12px 40px; background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; color: " + t["text"] + "; font-size: 14px; outline: none; transition: border-color 0.2s; }
.ks-search-input:focus { border-color: " + t["primary"] + "; }
.ks-search-input::placeholder { color: " + t["text_muted"] + "; }
</style>";
}

func empty_state(icon, title, desc, action, t) {
    if t == none { t = dark_theme(); }

    let btn_html = "";
    if action != none {
        let variant = "primary";
        if "variant" in action { variant = action["variant"]; }
        btn_html = button(action["text"], action["url"], variant, t);
    }

    return "
<div class='ks-empty'>
    <div class='ks-empty-icon'>" + icon + "</div>
    <div class='ks-empty-title'>" + title + "</div>
    <div class='ks-empty-desc'>" + desc + "</div>
    " + btn_html + "
</div>
<style>
.ks-empty { text-align: center; padding: 60px 20px; background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; margin-bottom: 24px; }
.ks-empty-icon { font-size: 48px; margin-bottom: 16px; }
.ks-empty-title { font-size: 20px; font-weight: 600; color: " + t["text"] + "; margin-bottom: 8px; }
.ks-empty-desc { font-size: 14px; color: " + t["text_muted"] + "; margin-bottom: 20px; }
</style>";
}

func notification(msg, variant, dismissible, t) {
    if t == none { t = dark_theme(); }
    if variant == none { variant = "info"; }
    if dismissible == none { dismissible = true; }

    let color = t["info"];
    let icon = "ℹ";
    if variant == "success" { color = t["success"]; icon = "✔"; }
    elif variant == "warning" { color = t["warning"]; icon = "⚠"; }
    elif variant == "danger" { color = t["danger"]; icon = "✖"; }

    let close_btn = "";
    if dismissible == true {
        close_btn = "<span class='ks-notif-close' onclick='this.parentElement.style.display=\"none\"'>✕</span>";
    }

    return "
<div class='ks-notif ks-notif-" + variant + "' style='border-left: 4px solid " + color + "'>
    <span class='ks-notif-icon' style='color:" + color + "'>" + icon + "</span>
    <span class='ks-notif-msg'>" + msg + "</span>
    " + close_btn + "
</div>
<style>
.ks-notif { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; margin-bottom: 12px; font-size: 14px; }
.ks-notif-icon { font-size: 16px; flex-shrink: 0; }
.ks-notif-msg { flex: 1; color: " + t["text"] + "; }
.ks-notif-close { cursor: pointer; color: " + t["text_muted"] + "; font-size: 14px; padding: 4px; }
.ks-notif-close:hover { color: " + t["text"] + "; }
</style>";
}

func star_rating(rating, max_stars, t) {
    if t == none { t = dark_theme(); }
    if max_stars == none { max_stars = 5; }

    let stars = "";
    for i in range(max_stars) {
        if i < int(rating) {
            stars = stars + "<span class='ks-star ks-star-filled'>★</span>";
        } elif i < rating {
            stars = stars + "<span class='ks-star ks-star-half'>★</span>";
        } else {
            stars = stars + "<span class='ks-star ks-star-empty'>★</span>";
        }
    }

    return "
<div class='ks-rating'>" + stars + " <span class='ks-rating-val'>" + str(rating) + "/" + str(max_stars) + "</span></div>
<style>
.ks-rating { display: inline-flex; align-items: center; gap: 2px; }
.ks-star { font-size: 18px; }
.ks-star-filled { color: #f59e0b; }
.ks-star-half { color: #f59e0b; opacity: 0.5; }
.ks-star-empty { color: " + t["border"] + "; }
.ks-rating-val { font-size: 13px; color: " + t["text_muted"] + "; margin-left: 6px; }
</style>";
}

func tag_list(tags, t) {
    if t == none { t = dark_theme(); }

    let items = "";
    let colors = [t["primary"], t["success"], t["warning"], t["danger"], t["info"]];
    for i in range(len(tags)) {
        let color = colors[i % len(colors)];
        items = items + "<span class='ks-tag' style='background:" + color + "20;color:" + color + ";border:1px solid " + color + "40'>" + tags[i] + "</span>";
    }

    return "
<div class='ks-tags'>" + items + "</div>
<style>
.ks-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.ks-tag { display: inline-block; padding: 4px 12px; border-radius: 16px; font-size: 13px; font-weight: 500; }
</style>";
}

func kanban(columns, t) {
    if t == none { t = dark_theme(); }

    let cols = "";
    for col in columns {
        let cards_html = "";
        let cards = col["cards"];
        for card in cards {
            let badge_html = "";
            if "badge" in card {
                let bc = t["primary"];
                if "badge_color" in card { bc = card["badge_color"]; }
                badge_html = "<span class='ks-kanban-badge' style='background:" + bc + "20;color:" + bc + "'>" + card["badge"] + "</span>";
            }
            let assignee_html = "";
            if "assignee" in card {
                let initials = "";
                let parts = card["assignee"].split(" ");
                for p in parts {
                    if p != "" { initials = initials + p[0].upper(); }
                    if len(initials) >= 2 { break; }
                }
                assignee_html = "<div class='ks-kanban-avatar' style='background:" + t["primary"] + "'>" + initials + "</div>";
            }
            cards_html = cards_html + "
<div class='ks-kanban-card'>
    <div class='ks-kanban-card-header'>" + card["title"] + "</div>
    " + badge_html + "
    " + (card["desc"] != none ? "<div class='ks-kanban-card-desc'>" + card["desc"] + "</div>" : "") + "
    " + assignee_html + "
</div>";
        }

        let count = str(len(cards));
        cols = cols + "
<div class='ks-kanban-col'>
    <div class='ks-kanban-col-header'>" + col["title"] + " <span class='ks-kanban-count'>" + count + "</span></div>
    <div class='ks-kanban-cards'>" + cards_html + "</div>
</div>";
    }

    return "
<div class='ks-kanban'>" + cols + "</div>
<style>
.ks-kanban { display: flex; gap: 16px; overflow-x: auto; padding-bottom: 16px; margin-bottom: 24px; }
.ks-kanban-col { min-width: 280px; flex: 1; background: " + t["bg"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 16px; }
.ks-kanban-col-header { font-size: 14px; font-weight: 600; color: " + t["text"] + "; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.ks-kanban-count { font-size: 12px; background: " + t["border"] + "; color: " + t["text_muted"] + "; padding: 2px 8px; border-radius: 10px; }
.ks-kanban-cards { display: flex; flex-direction: column; gap: 8px; }
.ks-kanban-card { background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 12px; }
.ks-kanban-card-header { font-size: 14px; font-weight: 500; color: " + t["text"] + "; margin-bottom: 6px; }
.ks-kanban-card-desc { font-size: 13px; color: " + t["text_muted"] + "; margin-bottom: 8px; }
.ks-kanban-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; margin-bottom: 8px; }
.ks-kanban-avatar { width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: #fff; font-size: 10px; font-weight: 600; }
</style>";
}

func stat_grid(stats, t) {
    if t == none { t = dark_theme(); }

    let items = "";
    for s in stats {
        let trend_html = "";
        if "trend" in s {
            let tc = t["success"];
            let arrow = "↑";
            if s["trend"] < 0 { tc = t["danger"]; arrow = "↓"; }
            trend_html = "<div class='ks-stat-trend' style='color:" + tc + "'>" + arrow + " " + str(s["trend"]) + "%</div>";
        }
        let icon_html = "";
        if "icon" in s { icon_html = "<div class='ks-stat-icon' style='color:" + t["primary"] + "'>" + s["icon"] + "</div>"; }
        items = items + "
<div class='ks-stat-grid-item'>
    " + icon_html + "
    <div class='ks-stat-grid-val'>" + str(s["value"]) + "</div>
    <div class='ks-stat-grid-label'>" + s["label"] + "</div>
    " + trend_html + "
</div>";
    }

    return "
<div class='ks-stat-grid'>" + items + "</div>
<style>
.ks-stat-grid { display: grid; grid-template-columns: repeat(" + str(len(stats)) + ", 1fr); gap: 16px; margin-bottom: 24px; }
.ks-stat-grid-item { background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; padding: 20px; }
.ks-stat-grid-icon { font-size: 20px; margin-bottom: 8px; }
.ks-stat-grid-val { font-size: 28px; font-weight: 700; color: " + t["text"] + "; }
.ks-stat-grid-label { font-size: 13px; color: " + t["text_muted"] + "; margin-top: 4px; }
.ks-stat-trend { font-size: 13px; font-weight: 500; margin-top: 8px; }
</style>";
}

func alert_banner(title, msg, variant, actions, t) {
    if t == none { t = dark_theme(); }
    if variant == none { variant = "info"; }

    let color = t["info"];
    let icon = "ℹ";
    if variant == "success" { color = t["success"]; icon = "✔"; }
    elif variant == "warning" { color = t["warning"]; icon = "⚠"; }
    elif variant == "danger" { color = t["danger"]; icon = "✖"; }

    let btns = "";
    if actions != none {
        for act in actions {
            btns = btns + button(act["text"], act["url"], "outline", t);
        }
    }

    return "
<div class='ks-alert-banner' style='border-left:4px solid " + color + "'>
    <div class='ks-alert-banner-icon' style='color:" + color + "'>" + icon + "</div>
    <div class='ks-alert-banner-content'>
        <div class='ks-alert-banner-title'>" + title + "</div>
        <div class='ks-alert-banner-msg'>" + msg + "</div>
    </div>
    <div class='ks-alert-banner-actions'>" + btns + "</div>
</div>
<style>
.ks-alert-banner { display: flex; align-items: center; gap: 16px; padding: 16px 20px; background: " + t["surface"] + "; border: 1px solid " + t["border"] + "; border-radius: " + t["radius"] + "; margin-bottom: 16px; }
.ks-alert-banner-icon { font-size: 24px; flex-shrink: 0; }
.ks-alert-banner-content { flex: 1; }
.ks-alert-banner-title { font-size: 15px; font-weight: 600; color: " + t["text"] + "; }
.ks-alert-banner-msg { font-size: 14px; color: " + t["text_muted"] + "; margin-top: 2px; }
.ks-alert-banner-actions { display: flex; gap: 8px; flex-shrink: 0; }
</style>";
}

func footer_bottom(links, brand, copyright, t) {
    if t == none { t = dark_theme(); }
    if brand == none { brand = "KentScript"; }

    let link_html = "";
    if links != none {
        for link in links {
            link_html = link_html + "<a href='" + link["url"] + "' class='ks-fb-link'>" + link["text"] + "</a>";
        }
    }

    return "
<footer class='ks-footer-bottom'>
    <div class='ks-footer-bottom-inner'>
        <span class='ks-footer-bottom-brand'>" + brand + "</span>
        <div class='ks-footer-bottom-links'>" + link_html + "</div>
        <span class='ks-footer-bottom-copy'>" + copyright + "</span>
    </div>
</footer>
<style>
.ks-footer-bottom { background: " + t["surface"] + "; border-top: 1px solid " + t["border"] + "; padding: 16px 24px; }
.ks-footer-bottom-inner { max-width: 1200px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.ks-footer-bottom-brand { font-size: 16px; font-weight: 700; color: " + t["primary"] + "; }
.ks-footer-bottom-links { display: flex; gap: 20px; }
.ks-fb-link { color: " + t["text_muted"] + "; font-size: 14px; text-decoration: none; }
.ks-fb-link:hover { color: " + t["text"] + "; }
.ks-footer-bottom-copy { font-size: 13px; color: " + t["text_muted"] + "; }
</style>";
}

export {
    dark_theme, light_theme, midnight_theme, custom_theme,
    navbar, card, button, input, textarea, table,
    alert, badge, modal, tabs, sidebar,
    form, dropdown, progress_bar, tooltip, accordion, toast,
    pagination, footer, dropdown_menu, code_block, stat_card,
    divider, avatar, toggle, skeleton,
    page, page_from_string,
    hero, feature_grid, pricing_table, testimonial, timeline, steps,
    chart_bar, breadcrumbs, team_card, chat_bubble, chat,
    login_form, search_bar, empty_state, notification, star_rating,
    tag_list, kanban, stat_grid, alert_banner, footer_bottom
};
