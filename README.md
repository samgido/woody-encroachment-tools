# Woody Encroachment Tools

The woody encroachment tools are a suite of scripts which use Meta's CHMv2 model to approximate and analyze the encroachment of woody vegetation over a defined area. 
<!-- The scripts were initially developed for and used in [THIS PAPER] -->

> [!WARNING]
> This repository is a WIP 

## Setup

The very first step is to get access to Meta's CHMv2 model, which is done via Hugging Face. 
Visit [this site](https://huggingface.co/facebook/dinov3-vitl16-chmv2-dpt-head), create an account and request access to the model, you'll use this account at a later step in the setup. 
They usually grant access within a few days. 

I'd recommend using conda to manage the python environment for this project, this section contains a few steps to setup the environment from scratch with conda.
Alternatively, install the required packages (declared in `environment.yml`) and skip to the required setup section. 

### Recommended Setup

First, go [here](https://conda-forge.org/download/) to download conda. 

> [!TIP]
> On Windows, an easy way to install conda is with the command `winget install CondaForge.Miniforge3`. Then run `conda init` in the Miniforge Prompt app. 
>
> On Mac, with `brew install --cask miniforge`. 

Clone this repository, enter the repository directory in the terminal, and run this command to create a conda environment, called 'we-tools', for the project 

```
conda create -f environment.yml 
```

This may take a few minutes, it downloads all of the packages from `environment.yml`. 
You can activate the environment with `conda activate we-tools`. 

### Required Setup 

Just one step, run `hf auth login` (with the environment activated) and follow the steps to link the Hugging Face account created earlier. 
Without this step, you won't be able to use the CHMv2 model. 

## General Use 

Always be sure the environment is activated before running the tools. 
Then, prepare a vector data file for the sites you want analyzed. 
Run this command to process the vector data 

```
python main.py /path/to/vector/data
```

> [!IMPORTANT]
> Use polygons when drawing site shapes, otherwise the analysis might not give the expected results. 

Then, the program should create a folder next to the input shapefile. 
Inside this folder, one folder is created for each geometry in the file. 
The script will place the results for each site into their respective folders. 

For example, running `python main.py /path/to/my-sites.shp` would create a folder structure like this 

```
my-sites.shp
my-sites/
├─ site1/
├─ site2/
├─ site3/
```

> [!TIP]
> If an attribute named 'Site' is included in the vector data, the value will be used to name the output folders for each site. 
> Otherwise, they will be named `site1`, `site2`, etc.


Each site folder should have the same files in them. If not, check the output of the program to see what went wrong. 

## Acknowledgements

This project uses pre-trained weights from [Meta's CHMv2 & DINOv3 model](https://github.com/facebookresearch/dinov3).
Thank you to the original authors and the World Resources Institute for releasing these models. 

## Known Issues

- On Windows, I get import errors from the `rasterio` python package if I have GDAL on my path anywhere. 
Try removing GDAL from path, or uninstalling entirely, if you have similar issues. 
Some info [here](https://github.com/conda-forge/rasterio-feedstock/issues/349#issuecomment-5522251038). 
