import os
from PyQt5.QtWidgets import QMessageBox


def get_next_available_version(path, base_suffix="_v"):
    base, ext = os.path.splitext(path)
    i = 2
    new_path = f"{base}{base_suffix}{i}{ext}"
    while os.path.exists(new_path):
        i += 1
        new_path = f"{base}{base_suffix}{i}{ext}"
    return new_path


def resolve_output_path_with_user_prompt(output_path, output_filename):
    if os.path.exists(output_path):
        box = QMessageBox()
        box.setWindowTitle("File already exists")
        box.setText(f"The file '{output_filename}' already exists.\nWhat do you want to do?")
        overwrite_button = box.addButton("Overwrite", QMessageBox.AcceptRole)
        save_v2_button = box.addButton("Save as new version", QMessageBox.ActionRole)
        cancel_button = box.addButton("Don't Save", QMessageBox.RejectRole)
        box.exec_()

        if box.clickedButton() == save_v2_button:
            output_path = get_next_available_version(output_path)
        elif box.clickedButton() == cancel_button:
            print("Export canceled by user.")
            return None
    return output_path

