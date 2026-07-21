// Recent Projects: a thumbnail strip backed by app/projects.py's local
// SQLite history. Every successful STL export gets saved server-side;
// this module lists them and fetches a given one back (params + the
// original photo) so app.js can restore the full editing state.

const el = (id) => document.getElementById(id);

export async function refreshRecentProjects(onSelect) {
  const strip = el("recentStrip");
  if (!strip) return;
  try {
    const res = await fetch("/api/projects?limit=30");
    if (!res.ok) return;
    const items = await res.json();

    strip.innerHTML = "";
    if (items.length === 0) {
      strip.innerHTML = '<p class="hint-small">Your exports will show up here.</p>';
      return;
    }

    for (const item of items) {
      strip.appendChild(buildTile(item, onSelect));
    }
  } catch (e) {
    // Best-effort: the Recent strip just stays as it was on failure.
  }
}

function buildTile(item, onSelect) {
  const tile = document.createElement("div");
  tile.className = "recent-tile";

  const date = new Date(item.created_at * 1000).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

  const openBtn = document.createElement("button");
  openBtn.type = "button";
  openBtn.className = "recent-tile-open";
  openBtn.title = `${item.name} · ${date}`;
  openBtn.innerHTML = `
    <img src="/api/projects/${item.id}/thumbnail" alt="" loading="lazy" />
    <span class="recent-tile-name">${escapeHtml(item.name)}</span>
  `;
  openBtn.addEventListener("click", () => onSelect(item.id));

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "recent-tile-delete";
  deleteBtn.title = "Remove from history";
  deleteBtn.textContent = "×";
  deleteBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    if (!confirm(`Remove "${item.name}" from Recent? This can't be undone.`)) return;
    await fetch(`/api/projects/${item.id}`, { method: "DELETE" });
    refreshRecentProjects(onSelect);
  });

  tile.appendChild(openBtn);
  tile.appendChild(deleteBtn);
  return tile;
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

export async function loadProject(id) {
  const res = await fetch(`/api/projects/${id}`);
  if (!res.ok) throw new Error("Could not load that project");
  const project = await res.json();

  const imgRes = await fetch(`/api/projects/${id}/image`);
  if (!imgRes.ok) throw new Error("Could not load the saved photo");
  const blob = await imgRes.blob();
  const file = new File([blob], project.name, { type: blob.type });

  return { params: project.params, file };
}
