import os
import shutil
import zipfile
import requests
import platform, subprocess
import time
import logging

from pathlib import Path

start_time = time.time()

os_type = platform.system()
if os_type == "Darwin" and platform.processor() == "arm":
    os_type = "Arm"

OS_MAP = {
    "Windows": "chromedriver-win64",
    "Linux": "chromedriver-linux64",
    "Darwin": "chromedriver-mac-x64",
    "Arm": "chromedriver-mac-arm64",
}

OS_NAME = {
    "Windows": "win64",
    "Linux": "linux64",
    "Darwin": "mac-x64",
    "Arm": "mac-arm64",
}
zip_name = OS_MAP.get(os_type)
os_name = OS_NAME.get(os_type)

CHROMEDRIVER_DIR = Path(f"{os.getcwd()}")
CHROMEDRIVER_PATH = CHROMEDRIVER_DIR / "chromedriver" / "chromedriver"


def get_installed_version():
    if CHROMEDRIVER_PATH.exists():
        try:
            version = os.popen(f"{CHROMEDRIVER_PATH} --version").read().split()[1]
            return version
        except Exception:
            return None


def get_latest_version():
    url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
    else:
        raise Exception(f"Unsupported url: {response.status_code} / {url}")

    return data["channels"]["Stable"]["version"]


def get_download_url(version):
    os_type = platform.system()
    if os_type == "Darwin" and platform.processor() == "arm":
        os_type = "Arm"

    zip_name = OS_MAP.get(os_type)
    if not zip_name:
        raise Exception(f"Unsupported OS: {os_type}")

    download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/{os_name}/{zip_name}.zip"
    return download_url


def download_and_install(version):
    download_url = get_download_url(version)
    zip_path = CHROMEDRIVER_DIR / f"{zip_name}.zip"

    response = requests.get(download_url, stream=True)
    response.raise_for_status()

    with open(zip_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024):
            file.write(chunk)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(CHROMEDRIVER_DIR)

    os.remove(zip_path)

    if platform.system() != "Windows":
        os.chmod(CHROMEDRIVER_DIR / f"{zip_name}" / "chromedriver", 0o755)


def download_logic():
    installed_version = get_installed_version()
    latest_version = get_latest_version()

    print(f"Installedw chromedriver version: {installed_version}")
    print(f"Letest chromedriver version: {latest_version}")

    if installed_version is None or installed_version != latest_version:
        print("Installing/updateing chromedriver...")

        shutil.rmtree(CHROMEDRIVER_PATH / f"{zip_name}", ignore_errors=True)
        CHROMEDRIVER_DIR.mkdir(parents=True, exist_ok=True)

        download_and_install(latest_version)

        print("download success")

        extracted_folder = CHROMEDRIVER_DIR / f"{zip_name}"
        for file in extracted_folder.iterdir():
            if file.name != "chromedriver":
                file.unlink()

        os.rename(extracted_folder, "chromedriver")

        print(f"chromedriver installed/update to version {latest_version}")
    else:
        print("chromedriver is already up to date.")


# def final_logic(current_version, latest_version, p1, p2, p3):
#     os.path.join(CHROMEDRIVER_PATH, "chromedriver", f"{os_type}", f"{os.getcwd()}")
#     if current_version == latest_version:
#         logger = logging.getLogger(name="Chromedriver Download Log")
#         logger.info(logger)

#     elif current_version != latest_version:
#         latest_version = get_download_url(p1)
#         if p2 == p3:
#             pass
#         elif p2 != p3:
#             get_latest_version(latest_version)


if __name__ == "__main__":
    download_logic()
    print(f"{time.time() - start_time:.4f} sec")
