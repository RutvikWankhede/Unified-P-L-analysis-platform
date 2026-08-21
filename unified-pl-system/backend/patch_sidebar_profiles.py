import os
import re

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend_v2"))

print(f"Patching sidebar profiles in {FRONTEND_DIR}...")

html_files = [f for f in os.listdir(FRONTEND_DIR) if f.endswith(".html")]

target_pattern = r'<div class="p-4 border-t border-slate-200 space-y-4">.*?</div>\s*</div>\s*</aside>'

# Replacement with clean, dark-mode ready layout
new_profile_block = """<div class="p-4 border-t border-slate-200 dark:border-slate-800 space-y-4">
      <div class="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl">
        <div class="flex items-center justify-between text-xs mb-1">
          <span class="text-slate-500 dark:text-slate-400">Organization</span>
          <span class="px-1.5 py-0.5 bg-primary/10 text-primary dark:text-indigo-400 rounded text-[9px] font-bold">ENTERPRISE</span>
        </div>
        <p class="font-bold text-sm text-slate-900 dark:text-white">Acme Corporation</p>
      </div>
      <div class="flex items-center gap-3 p-2">
        <div class="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center font-bold text-base shadow-sm" id="global-user-initials">A</div>
        <div class="flex-1 overflow-hidden">
          <p class="font-semibold text-sm text-slate-900 dark:text-white truncate" id="global-username">Admin</p>
          <p class="text-xs text-slate-500 dark:text-slate-400 truncate" id="global-user-role">Administrator</p>
        </div>
      </div>
      <div class="flex justify-between gap-1 text-xs">
        <a href="profile.html" class="flex-1 text-center py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg text-slate-700 dark:text-slate-300 font-semibold transition-colors">Profile</a>
        <a href="settings.html" class="flex-1 text-center py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg text-slate-700 dark:text-slate-300 font-semibold transition-colors">Settings</a>
        <button onclick="window.auth.logout()" class="flex-1 text-center py-2 bg-red-50 dark:bg-red-950/20 hover:bg-red-100 dark:hover:bg-red-950/40 rounded-lg text-red-600 dark:text-red-400 font-semibold transition-colors">Logout</button>
      </div>
    </div>
  </aside>"""

for filename in html_files:
    if filename in ["index.html", "login.html", "forgot-password.html"]:
        continue
    path = os.path.join(FRONTEND_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # We match dotall since the pattern spans multiple lines
    new_content, count = re.subn(target_pattern, new_profile_block, content, flags=re.DOTALL)
    if count > 0:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  Patched profile in {filename}")
    else:
        # Fallback simpler match just in case
        fallback_pattern = r'<div class="p-4 border-t border-slate-200 space-y-4">.*?logout.*?</aside>'
        new_content, count = re.subn(fallback_pattern, new_profile_block, content, flags=re.DOTALL)
        if count > 0:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  Patched profile via fallback in {filename}")
        else:
            print(f"  WARNING: Profile block pattern not matched in {filename}")

print("Sidebar profile patching complete!")
