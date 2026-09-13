# Woody Encroachment Tools

> [!WARNING]
> This repository is a WIP 

These scripts were built to estimate the cover of woody vegetation over a defined area, typically a watershed. 
They were initially developed for and used in [THIS PAPER]

## Setup

The very first step is to get access to Meta's CHMv2 model. Visit [this site](https://huggingface.co/facebook/dinov3-vitl16-chmv2-dpt-head), create an account and request access to the model, you'll use this account at a later step. 
They usually grant access within a few days. 

Before running the code, run the following commands to set up the environment. 
This project has some heavy dependencies, so we use the [conda](https://conda-forge.org/download/) package manager to keep everything neat. 

> [!TIP]
> On Windows, conda can easily be installed by running the command `winget install CondaForge.Miniforge3` in the terminal. Then run `conda init` in the Miniforge Prompt application. 
>
> On Mac, with `brew install --cask miniforge`. 

With `conda`, create an environment for this project with the necessary packages 

```
conda create -f environment.yml 
```

This may take a few minutes. 
Next, we need to link this python environment with the account that has access to Meta's model, so first activate the environment 

```
conda activate we-tools
```

And run `hf auth login` to login to the hugging face account by following the instructions printed to the terminal. 
That should be all of the setup steps. 

## General Use 

First, activate the conda environment with the same command from above. 
Then, prepare a shapefile sites you want analyzed, and run the command 

```
python main.py /path/to/shapefile
```

> [!WARNING]
> On Windows, I get import errors from `rasterio` if I have GDAL on my path anywhere. 
> Try removing GDAL from path, or uninstalling entirely, if you have similar issues. 
> Some info [here](https://github.com/conda-forge/rasterio-feedstock/issues/349#issuecomment-5522251038).


Assuming the program was able to read the shapefile, a folder is created next to the file. 
Inside this folder, a folder is created for each site geometry in the file, and once the process is complete all results will be in these folders. 

For example, running `python main.py /path/to/my-sites.shp` would create a folder structure like for the output

```
my-sites.shp
my-sites/
├─ site1/
├─ site2/
├─ site3/
```

Each site folder should have the same files in them. If not, check the output of the program to see what went wrong. 

## Acknowledgements

This project uses pre-trained weights from [Meta's CHMv2 & DINOv3 model](https://github.com/facebookresearch/dinov3).
Thank you to the original authors and the World Resources Institute for releasing these models. 
