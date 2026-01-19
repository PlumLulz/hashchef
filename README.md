# hashchef
Hashchef is a lightweight Hashcat wrapper to help automate basic workflows. During my everyday hash cracking I tend to follow specific workflows. These workflows change slightly based off the hash algorithm, time available, number of hashes, etc. The goal with this project was to create a very lightweight program to automate some of these simple workflows. I wanted a modular system that allowed me to start different Hashcat workflows with one command. This program was inspired by the semi conductor industries use of "recipes." These "recipes" use steps to run different capabilites on manufacturing tools. Currently only attack modes 0 and 3 are supported. The main reason for this is because they are the two main modes I use in everyday normal cracking. 

## Setup / Usage:
This program was designed to be lightweight and simple to use. With that in mind there is no setup needed with your Hashcat install. Just place the hashchef.py file in your root Hashcat directory. Optionally you can create a directory named recipes for all of your recipe files. 

#### Preview Hashcat commands for each step in recipe:
```
python3 hashchef.py hashfile.txt cracked.txt 0 hc_md5.recipe -preview
```
#### Start running recipe with a verbose output:
```
python3 hashchef.py hashfile.txt cracked.txt 0 hc_md5.recipe -verbose
```
#### Help flag:
<img width="992" height="353" alt="Screenshot 2026-01-07 at 04 09 13" src="https://github.com/user-attachments/assets/966937a1-02e1-46d1-a478-7dfcb7727a93" />

## Hashchef Recipes
Hashchef uses recipe files to create different Hashcat workflows. A recipe file is just a simple JSON object, making creation of new recipes very easy. Below is the structure, variable details, and variable data type for recipes. Please review the details below to make sure you are passing the correct data types for each variable. There will also be example recipes to reference in this repo. Recipes can be saved with a .json or .recipe file extension. 

#### Hashchef JSON recipe structure:
```
.
├── recipe_name: Name of custom recipe. (str)
├── recipe_steps: Object containing each step of custom recipe. First step starts with step_0. (object)
│   └── step_*: Object containing custom step variables. (object)
│       ├── step_name: Name of step in custom recipe. (str)
│       ├── attack_mode: Hashcat attack mode used for step. Only 0 and 3 are currently supported. (int)
│       ├── wordlist: If no wordlist is needed pass null. Wordlists should be put in a list with their full paths, whole directories can be used. (null, list)
│       ├── mask: If no mask is needed pass null. Put mask sequence in a string. (str)
│       ├── exclude: Wordlists to exclude from running. If no exclusions are needed pass null. Excluded wordlists can be placed in a list with just their names, no paths needed. (null, list)
│       ├── bypass_timeout: Time in minutes to bypass current wordlist/mask that is running in step. If no bypass timeout is desired pass null. (null, int)
│       ├── step_timeout: Time in minutes to bypass the whole current step. Once timeout is reached the next step will start if available. (null, int)
│       └── optflags: List of optional Hashcat flags for step. If no optional flags needed pass an empty list. Do NOT use the --status and --status-timer flags, the program uses them to read the Hashcat output properly. (list)
└── hashes_api: Hashes.com upload API integration details. Pass null if not needed. (null, object)
    ├── api_key: Hashes.com API key. (str)
    └── upload_frequency: Interval in seconds to upload new cracks to hashes.com. Pick a reasonable number to prevent potential spam to the hashes.com server. (int)
```

## Hashes.com upload API integration
Automatic uploads of cracks to hashes.com can be setup on a set interval. When enabled, a monitor will start before the first step of recipe. Every x seconds the output file will be checked for new cracks as the recipe runs. Only hashes that are new compared to last interval will be uploaded to hashes.com. This will help prevent unnecessary requests and limit the use of server resources. When using this feature make sure that you are choosing a reasonable interval to check for new cracks and upload. To set this feature up just add your hashes.com API key and preferred upload frequency to the hashes_api variable in your custom recipe. If auto uploads are not needed just pass null to the hashes_api variable. Below is an example of what to add to a recipe to enable automatic uploads.

#### Enable automatic hashes.com uploads:
```
"hashes_api": {
	"api_key": "Your hashes.com API key",
	"upload_frequency": 60
}
```

#### Disable automatic hashes.com uploads:
```
"hashes_api": null
```
