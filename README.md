# Generic_OTA_Package_Generation_Script

一个使用Python编写的脚本，比较两个Rom包的差异，并生成OTA增量更新包<br>
(A script that compares the differences between two Android Rom packages &amp; generates an OTA package.)

## Before use

使用此脚本不需要你做任何多余的事，只需要Python 3.x版本以及一个第三方库就行了<br>
(Using this script doesn't require you to do anything extra, just need Python 3.x & a extension library.)

在使用此脚本前，你需要先使用**pip**安装一个名为**bsdiff4**的第三方库<br>
(You need to install a extension library called **bsdiff4** with **pip** before using this script.)

在终端执行这条命令:<br>
(Execute this command at the terminal:)

```sh
pip3 install bsdiff4
```

此脚本当然也可以在Windows系统中使用，但是如果你在安装bsdiff4时遇到困难，请寻找非官方的二进制包并自行安装。你可以在<a href="https://www.lfd.uci.edu/~gohlke/pythonlibs/#bsdiff4">这里</a>找到它，请根据您的Python版本和系统架构进行选择<br>
(This script can of course also be used on Windows OS, but if you have trouble installing bsdiff4, you need look for unofficial binary packages and install it yourself. You can find it at <a href="https://www.lfd.uci.edu/~gohlke/pythonlibs/#bsdiff4">here</a>. Please choose according to your Python version and system architecture.)

## Usage

```sh
Generic OTA Package Generation Script vX.X
By Pzqqt
usage: mkota.py [-h] [-o OUTPUT] [-e EXT_MODELS] old_package new_package

positional arguments:
  old_package           old package path
  new_package           new package path

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        output OTA package name/path (default
                        OTA.zip)(default: ./OTA.zip)
  -e EXT_MODELS, --ext-models EXT_MODELS
                        additional model that allows for model
                        verification(default: None)
```

## Note

- 目前仅支持对Lollipop+的Rom包进行操作，不支持使用传统方法和特殊方法打包的Rom<br>
(Only Lollipop+ Rom supported. Not supported Rom of packaged with traditional methods or special methods.)
- 目前不支持对system-as-root设备的Rom包进行操作，因为我没有设备进行测试(笑)<br>
(Not supported to operate the Rom of any system-as-root device because I have no device to test.)
- 为什么使用bsdiff而不使用imgdiff?因为imgdiff在Windows系统下无法使用，其次bsdiff已经足够，imgdiff虽然更好但并非必须<br>
(Why use bsdiff instead of imgdiff? Because imgdiff is not available on Windows OS, secondly bsdiff is enough, imgdiff is better but not necessary.)

## License
- <a href="https://opensource.org/licenses/MIT">MIT</a>
