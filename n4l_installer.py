#!/usr/bin/env python3
"""
N4L Secure Access Wi-Fi Certificate Installer
For Ubuntu with GNOME desktop

Uses native GNOME dialogs (zenity) for a seamless desktop experience.
No additional Python packages required.
"""

import subprocess
import sys
import os
import shutil

TITLE = "N4L Secure Access Installer"
CERT_DEST_DIR = "/usr/local/share/ca-certificates"


def run_zenity(args):
    """Run a zenity command and return the result."""
    try:
        return subprocess.run(["zenity"] + args, capture_output=True, text=True)
    except FileNotFoundError:
        print("Error: zenity not found. Install it with: sudo apt install zenity")
        sys.exit(1)


def show_info(message):
    run_zenity(["--info", "--title", TITLE, "--text", message, "--width", "400"])


def show_error(message):
    run_zenity(["--error", "--title", TITLE, "--text", message, "--width", "400"])


def show_warning(message):
    run_zenity(["--warning", "--title", TITLE, "--text", message, "--width", "400"])


def select_certificate():
    """Open a native GNOME file picker to select a certificate file."""
    result = run_zenity([
        "--file-selection",
        "--title", "Select your N4L Certificate",
        "--filename", os.path.expanduser("~/"),
        "--file-filter", "Certificate Files (*.crt *.pem *.cer) | *.crt *.pem *.cer",
        "--file-filter", "All Files | *",
    ])

    if result.returncode != 0 or not result.stdout.strip():
        return None

    return result.stdout.strip()


def install_certificate(cert_path):
    """Install the certificate to the Ubuntu system trust store via pkexec.

    Ubuntu's update-ca-certificates only processes .crt files, so if the
    selected file has a different extension it is renamed on copy.
    """
    filename = os.path.basename(cert_path)
    name, ext = os.path.splitext(filename)

    # Ensure the destination file has a .crt extension
    if ext.lower() != ".crt":
        filename = name + ".crt"

    dest_path = os.path.join(CERT_DEST_DIR, filename)

    command = [
        "pkexec", "sh", "-c",
        f'cp "{cert_path}" "{dest_path}" && chmod 644 "{dest_path}" && update-ca-certificates',
    ]

    try:
        return subprocess.run(command, capture_output=True, text=True)
    except Exception as e:
        show_error(f"An unexpected error occurred:\n{e}")
        return None


def main():
    # Preflight checks
    if not shutil.which("zenity"):
        print("Error: zenity is not installed.")
        print("Install it with: sudo apt install zenity")
        sys.exit(1)

    if not shutil.which("pkexec"):
        show_error(
            "pkexec is not available.\n\n"
            "Install policykit-1 with:\n"
            "sudo apt install policykit-1"
        )
        sys.exit(1)

    # Step 1 — Select the certificate file
    cert_path = select_certificate()

    if not cert_path:
        sys.exit(0)  # User cancelled the file picker

    if not os.path.isfile(cert_path):
        show_error(f"Selected file does not exist:\n{cert_path}")
        sys.exit(1)

    # Step 2 — Confirm before installing
    filename = os.path.basename(cert_path)
    confirm = run_zenity([
        "--question",
        "--title", TITLE,
        "--text",
        f"Install the following certificate to the system trust store?\n\n"
        f"File: {filename}\n"
        f"Destination: {CERT_DEST_DIR}/",
        "--width", "400",
    ])

    if confirm.returncode != 0:
        sys.exit(0)  # User declined

    # Step 3 — Install with privilege escalation
    result = install_certificate(cert_path)

    if result is None:
        sys.exit(1)

    if result.returncode == 0:
        show_info(
            "Certificate installed successfully!\n\n"
            "Open your Wi-Fi settings, select the\n"
            "N4L Secure Access network, and choose your\n"
            "newly installed certificate from the CA list."
        )
    elif result.returncode == 126:
        show_warning("Authentication was cancelled.")
    else:
        show_error(f"Failed to install certificate.\n\nDetails:\n{result.stderr}")


if __name__ == "__main__":
    main()
