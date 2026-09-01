def format_staff_html(staff):
    if not staff:
        return "<p>No staff found.</p>"

    html = "<ul>"
    for staff_member in staff:
        html += (
            f"<li>{staff_member['staff_id']} - "
            f"{staff_member['given_name']} {staff_member['family_name']} - {staff_member['department']}</li>"
        )
    html += "</ul>"
    return html

def format_staffs_html(staff_list):
    if not staff_list:
        return "<p>No staff found in this department.</p>"

    html = "<ul>"
    for staff_member in staff_list:
        html += (
            f"<li>{staff_member['staff_id']} - "
            f"{staff_member['given_name']} {staff_member['family_name']} - {staff_member['department']}</li>"
        )
    html += "</ul>"
    return html


def format_staff_detail_html(staff_member):
    return (
        f"<p>ID: {staff_member['staff_id']}<br>"
        f"Name: {staff_member['given_name']} {staff_member['family_name']}<br>"
        f"Department: {staff_member['department']}</p>"
    )