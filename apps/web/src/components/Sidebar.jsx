import { useState } from "react";

const NAV_ITEMS = [
  { id: "parent",    label: "Live Session",  icon: "●" },
  { id: "symbols",   label: "Voice Board", icon: "▦" },
  { id: "research",  label: "Care Agent", icon: "?" },
  { id: "sessions",  label: "Evidence Timeline",  icon: "≡" },
];

const AVATAR_COLORS = ["#2563eb", "#0f766e", "#ca8a04", "#dc2626", "#0369a1", "#047857"];

function initials(name) {
  return name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
}

function avatarColor(name) {
  return AVATAR_COLORS[name.charCodeAt(0) % AVATAR_COLORS.length];
}

export default function Sidebar({ child, children, onSelectChild, onAddChild, activePage, onNavigate }) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [showSwitcher, setShowSwitcher] = useState(false);
  const [form, setForm] = useState({ name: "", age: "" });
  const [loading, setLoading] = useState(false);

  async function handleAdd(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await onAddChild(form.name, form.age);
      setForm({ name: "", age: "" });
      setShowAddForm(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-mark">B</div>
        <div>
          <div className="logo-title">Bridge</div>
          <div className="logo-sub">Care Agent</div>
        </div>
      </div>

      <div className="sidebar-profile-section">
        {child ? (
          <>
            <div className="profile-card">
              <div className="avatar" style={{ background: avatarColor(child.name) }}>
                {initials(child.name)}
              </div>
              <div className="profile-info">
                <div className="profile-name">{child.name}</div>
                <div className="profile-age">Age {child.age}</div>
              </div>
              {children.length > 1 && (
                <button
                  className="profile-switch-btn"
                  onClick={() => setShowSwitcher(v => !v)}
                >
                  ↕
                </button>
              )}
            </div>

            {showSwitcher && (
              <div className="profile-switcher-dropdown">
                {children.map(c => (
                  <button
                    key={c.id}
                    className={`profile-switcher-option ${c.id === child.id ? "active-opt" : ""}`}
                    onClick={() => { onSelectChild(c); setShowSwitcher(false); }}
                  >
                    <div className="avatar" style={{ background: avatarColor(c.name), width: 28, height: 28, fontSize: "0.72rem" }}>
                      {initials(c.name)}
                    </div>
                    {c.name}
                  </button>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="profile-empty">
            <div className="profile-empty-text">No profile selected</div>
          </div>
        )}
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(item => (
          <button
            key={item.id}
            className={`nav-item ${activePage === item.id ? "active" : ""}`}
            onClick={() => onNavigate(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        {showAddForm ? (
          <form onSubmit={handleAdd} className="add-child-form">
            <input
              placeholder="Child's name"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              required
            />
            <input
              placeholder="Age"
              type="number"
              min="0"
              max="25"
              step="0.5"
              value={form.age}
              onChange={e => setForm(f => ({ ...f, age: e.target.value }))}
              required
            />
            <div className="form-buttons">
              <button type="submit" disabled={loading} className="btn-success">
                {loading ? "Adding..." : "Add"}
              </button>
              <button type="button" className="btn-ghost" onClick={() => setShowAddForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <button className="add-child-btn" onClick={() => setShowAddForm(true)}>
            <span>+</span> Add Child
          </button>
        )}
      </div>
    </aside>
  );
}
