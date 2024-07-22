# Installation
This has been tested on Ubuntu 22.04 with Python 3.11 only right now.

1. Make sure you have downloaded Ollama (`curl -fsSL https://ollama.com/install.sh | sh`) and then `ollama pull codestral`
2. Create a Python Environment (recommended to use Miniconda)
   1. `mkdir -p ~/miniconda3`
   2. `wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh`
   3. `bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3`
   4. `rm -rf ~/miniconda3/miniconda.sh`
   5. `~/miniconda3/bin/conda init bash`
   6. `conda create -n autocommenter python=3.11`
   7. `conda activate autocommenter`
 7. `pip install -r requirements.txt` to install the dependencies for the repo

# Setup

1. Make sure you create a folder called `./codebases` and then `git clone` your repo there.

# Usage

Just run `python python_extractor.py`!

It is recommended to afterwards generate a git branch called `documentation` afterwards and then generate pull request to the branch (this will done automatically in future releases)
