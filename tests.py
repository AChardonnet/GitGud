import gitGud
import os
import shutil

gitGud.init(".")
os.system("pause")
gitGud.add(["README.md", "gitGud.py", "tests.py"])
os.system("pause")
gitGud.commit("A Message", "Someone")
os.system("pause")
# Modify Readme
gitGud.status()
os.system("pause")
gitGud.diff()


os.system("pause")

testDirectory = os.path.join(os.getcwd(), ".gitGud")
if os.path.isdir(testDirectory):
    try:
        shutil.rmtree(testDirectory)
        print(f"Deleted directory: {testDirectory}")
    except Exception as e:
        print(f"Failed to delete {testDirectory}: {e}")
else:
    print(f"No asset directory at: {testDirectory}")
