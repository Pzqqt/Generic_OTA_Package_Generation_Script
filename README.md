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
(This script can of course also be used on Windows OS, but if you have trouble installing bsdiff4, you need look for unofficial binary packages and install it yourself. You can find it <a href="https://www.lfd.uci.edu/~gohlke/pythonlibs/#bsdiff4">at here</a>. Please choose according to your Python version and system architecture.)

## Usage

```sh
Generic OTA Package Generation Script vX.X
By Pzqqt
Usage: mkota.py <old_package_path> <new_package_path> [ota_package_name] [--ext-models [model_1] [model_2] ...]

    <old_package_path>                     : old package file path
    <new_package_path>                     : new package file path
    [ota_package_name]                     : custom generated OTA package name (default OTA.zip)
    [--ext-models [model_1] [model_2] ...] : additional model that allows for model verification
```

## Note

- 目前仅支持对Lollipop+的Rom包进行操作，不支持使用传统方法和特殊方法打包的Rom，不支持Treble Rom(含有vendor.new.dat(.br))<br>
(Only Lollipop+ Rom supported. Not supported Rom of packaged with traditional methods or special methods. Not supported Treble Rom (with vendor.new.dat(.br)).)
- 本脚本在遍历Rom文件时会尝试从file_contexts(.bin)文件中获取/system中的文件和目录的SELinux属性，如果Rom没有file_contexts(.bin)文件，则会尝试调用**sudo**命令来挂载system镜像。<br>
如果Rom没有file_contexts(.bin)文件，并且你是在Windows系统下进行操作的，那么很抱歉，本工具将抛出异常并终止运行<br>
(When traversing the Rom file, this script will try to get the SELinux attribute of the files and directories in /system from the **file_contexts(.bin)** file. If Rom does not have a **file_contexts(.bin)** file, it will try to call the **sudo** command to mount the system image.<br>
If Rom doesn't have **file_contexts(.bin)** file and you are operating under Windows OS, then sorry, the tool will throw an exception and terminate the run.)
- 为什么使用bsdiff而不使用imgdiff?因为imgdiff在Windows系统下无法使用，其次bsdiff已经足够，imgdiff虽然更好但并非必须<br>
(Why use bsdiff instead of imgdiff? Because imgdiff is not available on Windows OS, secondly bsdiff is enough, imgdiff is better but not necessary.)

## License
- <a href="https://opensource.org/licenses/MIT">MIT</a>
