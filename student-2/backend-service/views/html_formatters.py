DEPARTMENT_PALETTE = [
    "#2c3a5e", "#a9812f", "#3f6c51", "#a2632a",
    "#8a3c3c", "#4a5a78", "#6b4e8e", "#2f7a72",
]


def _department_color(department):
    index = sum(ord(ch) for ch in department) % len(DEPARTMENT_PALETTE)
    return DEPARTMENT_PALETTE[index]


def _initials(given_name, family_name):
    return f"{given_name[:1]}{family_name[:1]}".upper()


def format_staff_row_html(staff_member):
    staff_id = staff_member["staff_id"]
    color = _department_color(staff_member["department"])
    initials = _initials(staff_member["given_name"], staff_member["family_name"])

    return f"""<tr id="staff-row-{staff_id}">
  <td>
    <div class="staff-id-cell">
      <div class="badge" style="background:{color}">{initials}</div>
      <div class="name-block">
        <div class="name">{staff_member['given_name']} {staff_member['family_name']}</div>
        <div class="id mono">STF-{staff_id}</div>
      </div>
    </div>
  </td>
  <td><span class="dept-pill" style="border-color:{color}; color:{color}">{staff_member['department']}</span></td>
  <td>{staff_member['employment_type']}</td>
  <td>{staff_member['email']}</td>
  <td>
    <div class="row-actions">
      <button class="icon-btn" data-action="edit" data-id="{staff_id}" type="button">Edit</button>
      <button class="icon-btn" data-action="remove" data-id="{staff_id}" data-name="{staff_member['given_name']} {staff_member['family_name']}" type="button">Remove</button>
    </div>
  </td>
</tr>"""


def format_staff_edit_row_html(staff_member):
    staff_id = staff_member["staff_id"]
    full_time_selected = "selected" if staff_member["employment_type"] == "Full-time" else ""
    part_time_selected = "selected" if staff_member["employment_type"] == "Part-time" else ""
    contractor_selected = "selected" if staff_member["employment_type"] == "Contractor" else ""

    return f"""<tr id="staff-row-{staff_id}">
  <td colspan="5">
    <form class="edit-row-form" data-action="update" data-id="{staff_id}">
      <input type="text" name="given_name" value="{staff_member['given_name']}" placeholder="Given name" required>
      <input type="text" name="family_name" value="{staff_member['family_name']}" placeholder="Family name" required>
      <input type="email" name="email" value="{staff_member['email']}" placeholder="Email" required>
      <input type="text" name="department" value="{staff_member['department']}" placeholder="Dept code" required>
      <select name="employment_type">
        <option value="Full-time" {full_time_selected}>Full-time</option>
        <option value="Part-time" {part_time_selected}>Part-time</option>
        <option value="Contractor"{contractor_selected}>Contractor</option>
      </select>
      <button type="submit" class="btn btn-primary btn-sm">Save</button>
      <button type="button" class="btn btn-ghost btn-sm" data-action="cancel-edit" data-id="{staff_id}">Cancel</button>
    </form>
  </td>
</tr>"""


def format_empty_row_html(message):
    return f'<tr><td colspan="5" class="empty-row">{message}</td></tr>'


def format_staff_html(staff_list):
    """Renders <tr> rows for the full staff list (used by GET /staff)."""
    if not staff_list:
        return format_empty_row_html("No staff found.")
    return "".join(format_staff_row_html(member) for member in staff_list)


def format_staffs_html(staff_list):
    """Renders <tr> rows for a filtered staff list (used by GET /staff/by-department)."""
    if not staff_list:
        return format_empty_row_html("No staff found in this department.")
    return "".join(format_staff_row_html(member) for member in staff_list)


def format_staff_detail_html(staff_member):
    return (
        f"<p>ID: {staff_member['staff_id']}<br>"
        f"Name: {staff_member['given_name']} {staff_member['family_name']}<br>"
        f"Department: {staff_member['department']}</p>"
    )


def format_form_message_html(message, is_error=False):
    css_class = "form-error" if is_error else "form-success"
    return f'<p class="{css_class}">{message}</p>'