/**
 * Mini-renderer Markdown -> HTML (sans dépendance) pour les livrables VITA-FORM.
 * Supporte: # ## ###, **gras**, *ital*, `code`, > quote, - / 1. listes, |tableaux|.
 */
function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function inline(s) {
  s = escapeHtml(s);
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/\*(.+?)\*/g, "<em>$1</em>");
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  return s;
}

export function renderMarkdown(md) {
  if (!md) return "";
  const lines = md.split("\n");
  const out = [];
  let inUl = false, inOl = false, inTable = false, tableHeader = false;

  const closeLists = () => {
    if (inUl) { out.push("</ul>"); inUl = false; }
    if (inOl) { out.push("</ol>"); inOl = false; }
  };
  const closeTable = () => {
    if (inTable) { out.push("</tbody></table>"); inTable = false; tableHeader = false; }
  };

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const line = raw.replace(/\s+$/, "");

    // table
    if (/^\|.*\|$/.test(line)) {
      const cells = line.slice(1, -1).split("|").map((c) => c.trim());
      const isSep = cells.every((c) => /^:?-+:?$/.test(c));
      if (!inTable) {
        closeLists();
        out.push('<table>');
        inTable = true; tableHeader = false;
      }
      if (isSep) { tableHeader = true; out.push("<tbody>"); continue; }
      if (!tableHeader) {
        out.push("<thead><tr>" + cells.map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead>");
      } else {
        out.push("<tr>" + cells.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>");
      }
      continue;
    } else {
      closeTable();
    }

    if (!line.trim()) { closeLists(); out.push(""); continue; }
    if (line.startsWith("### ")) { closeLists(); out.push(`<h3>${inline(line.slice(4))}</h3>`); continue; }
    if (line.startsWith("## ")) { closeLists(); out.push(`<h2>${inline(line.slice(3))}</h2>`); continue; }
    if (line.startsWith("# ")) { closeLists(); out.push(`<h1>${inline(line.slice(2))}</h1>`); continue; }
    if (line.startsWith("> ")) { closeLists(); out.push(`<blockquote>${inline(line.slice(2))}</blockquote>`); continue; }

    const ulMatch = line.match(/^\s*[-*]\s+(.*)$/);
    if (ulMatch) {
      if (!inUl) { closeLists(); out.push("<ul>"); inUl = true; }
      out.push(`<li>${inline(ulMatch[1])}</li>`);
      continue;
    }
    const olMatch = line.match(/^\s*\d+\.\s+(.*)$/);
    if (olMatch) {
      if (!inOl) { closeLists(); out.push("<ol>"); inOl = true; }
      out.push(`<li>${inline(olMatch[1])}</li>`);
      continue;
    }
    closeLists();
    out.push(`<p>${inline(line)}</p>`);
  }
  closeLists();
  closeTable();
  return out.join("\n");
}
